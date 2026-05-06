from github import Github
import base64
from dotenv import load_dotenv
import os
from typing_extensions import TypedDict,Annotated
from langgraph.graph import START,StateGraph,END
import requests
from langchain_groq import ChatGroq
import operator
from pydantic import BaseModel,Field
from langchain_core.prompts import ChatPromptTemplate
from config.cloudinary import upload_bytes_to_cloudinary
from config.database import collection_name
from models.project import Project
from schemas.schema import list_serial
from bson import ObjectId
from langgraph.types import Send
from typing import Literal
from pymongo import UpdateOne
import time
import random
from huggingface_hub import InferenceClient
import threading
load_dotenv()

cf_lock = threading.Lock()
github_token = os.getenv("GITHUB_API")
llm = ChatGroq(model="llama-3.1-8b-instant",temperature=0.5)

class SubGraphState(TypedDict):
    title:str
    readme:str
    description:str
    languages:dict
    mobile_url:str
    desktop_url:str
    updated_at: str

class SuperGraphState(TypedDict):
    details:Annotated[list[dict],operator.add]
    projects:Annotated[list[SubGraphState],operator.add]
    route:Literal["subGraph","end"]
    
def subGraph() -> StateGraph:
    class details(BaseModel):
        description: str = Field(description="A concise 8-line summary of the project's purpose and functionality.")
        languages: dict = Field(description="A dictionary of programming languages used and their estimated percentage.")

    detail_llm = llm.with_structured_output(details)
    
    def detail_generator(state:SubGraphState) -> dict:
        """It generate the description and what languages used through analysing readme of the project"""
        
        prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert Technical Writer and Portfolio Architect. 
            Your task is to analyze a GitHub README and extract structured project details.

            STRICT REQUIREMENTS:
            1. DESCRIPTION: Write a narrative description that is EXACTLY 8 lines long. 
            - Focus on the problem solved, the core features, and the unique value proposition.
            - Ensure the language is professional yet engaging for a portfolio visitor.
            - Use clear, descriptive imagery (this will be used to generate project thumbnails).
            2. LANGUAGES & TOOLS: List the primary programming languages and frameworks found.

            OUTPUT FORMAT:
            Return your response in a valid JSON-like structure (or plain text if preferred) with these keys:
            - description
            - languages"""
        ),
        (
            "human", 
            "Analyze the following README content and extract the details:\n\n{readme}"
        )
        ])
        formatted_message = prompt.format_messages(readme=state["readme"])
        result = None
        for attempt in range(5): 
            try:
                result = detail_llm.invoke(formatted_message)
                break 
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    print(f"Groq Rate Limit hit for {state['title']}. Waiting 10 seconds... (Attempt {attempt+1}/5)")
                    time.sleep(10)
                else:
                    print(f"Groq error: {e}")
                    raise e 
                    
        if not result:
            return {"description": "Description generation failed.", "languages": {}}
        
        return {
            "description":result.description,
            "languages":result.languages
        }
    
    def image_generator(state:SubGraphState) -> dict:
        refined_prompt = (
            f"A beautiful, high-resolution UI/UX mockup of a SaaS web application for: {state['description']}. "
            f"The interface features a dark mode theme with glowing neon blue and purple accents. "
            f"It has frosted glassmorphism panels, clean typography, and a professional Dribbble portfolio aesthetic. "
            f"Displayed in 3D isometric perspective."
        )
        
        # Point to your custom Cloudflare Worker
        API_URL = os.getenv("CLOUDFLARE_WORKER_URL")
        
        # Optional: If you secured your worker, pass the token. Otherwise, an empty dict is fine.
        headers = {"Authorization": f"Bearer {os.getenv('CLOUDFLARE_API_KEY')}"} if os.getenv('CLOUDFLARE_API_KEY') else {}
        
        dims = {
            "desktop": (1024, 768),
            "mobile": (768, 1024)
        }
        updates = {}
        
        for view_name, (w, h) in dims.items():
            for attempt in range(4):
                print(f"🚀 Fetching {view_name} for {state['title']} via YOUR Cloudflare Worker...")
                
                try:
                    # --- YOUR CUSTOM LOCK ---
                    with cf_lock:
                        time.sleep(2) # Just a small 2-second buffer
                        
                        # Make sure the JSON keys match what your Worker is expecting!
                        # Most basic CF setups expect {"prompt": "..."}
                        response = requests.post(
                            API_URL, 
                            headers=headers, 
                            json={
                                "prompt": refined_prompt,
                                # Optional: pass w/h if your worker code is written to accept them
                                # "width": w, "height": h 
                            },
                            timeout=60
                        )
                    # -------------------------
                    
                    if response.status_code == 200:
                        # Cloudflare workers usually return raw image bytes, which Cloudinary accepts instantly
                        url = upload_bytes_to_cloudinary(response.content)
                        if url:
                            updates[f"{view_name}_url"] = url
                            print(f"✅ Successfully uploaded {view_name} for {state['title']}")
                            break 
                    else:
                        print(f"❌ Worker Error {response.status_code}: {response.text}")
                        time.sleep(5)
                        
                except Exception as e:
                    print(f"⚠️ Request failed: {str(e)}")
                    time.sleep(5)
                    
        return updates
    graph = StateGraph(SubGraphState)
    graph.add_node("detail_generator",detail_generator)
    graph.add_node("image_generator",image_generator)
    graph.add_edge(START,"detail_generator")
    graph.add_edge("detail_generator","image_generator")
    graph.add_edge("image_generator",END)
    
    return graph.compile()

compiled_subgraph = subGraph()

def run_project_subgraph(state:SubGraphState) -> dict:
    result =  compiled_subgraph.invoke(state)
    return {"projects":[result]}

def fetch_all_repos_and_readmes(state:SuperGraphState) -> dict:
    """Iterates through all repositories and fetches their README content."""
    try:
        projects = list_serial(collection_name.find())
        existing_projects_map = {p["title"]: str(p.get("updated_at")) for p in projects}
        g = Github(github_token)
        user = g.get_user()
        
        repos = user.get_repos()
        ls = []
        for repo in repos:
            if len(ls) >= 5:
                print("\n✋ Reached batch limit of 5 projects. Stopping fetch for this run.")
                break
            
            repo_updated_str = str(repo.updated_at)
            
            if repo.name in existing_projects_map:
                db_updated_str = existing_projects_map[repo.name]
                
                if repo_updated_str == db_updated_str:
                    continue 
                else:
                    print(f"Update detected for {repo.name}! Processing new changes...")
            else:
                print(f"New project found: {repo.name}!")
                
            print(f"--- Processing: {repo.full_name} ---")
            try:
                readme = repo.get_readme()
                readme_content = base64.b64decode(readme.content).decode('utf-8')
                
                project_data = {
                    "title": repo.name,                        
                    "readme": readme_content,
                    "updated_at":repo_updated_str
                }
                ls.append(project_data)
                print(f"Successfully fetched data for {repo.name}")
                print(readme_content)
            
            except Exception:
                print(f"No README found for {repo.name}, skipping...")
                continue
        if ls == []:
            return {
                "route":"end"
            }
        return {
            "details":ls,
            "route":"subGraph"
        }
    except Exception as e:
        print(f"Critical error: {str(e)}")
        
def dispatch_sub_graph(state:SuperGraphState) -> list[Send]:
    """Dynamically create parallel subgraph task using send api"""
    if state.get("route") == "end":
        return END
    return [
        Send("run_project_subgraph",{"title":detail["title"],"readme":detail["readme"],"updated_at":detail["updated_at"]}) for detail in state["details"] 
    ]

def save_projects(state:SuperGraphState) -> dict:
    """Takes the aggregated list of project and save it to mongodb"""
    completed_projects = state.get("projects",[])
    
    if not completed_projects:
        print("No new project to save")
        return state
    
    print(f"Preparing project to save {len(completed_projects)} projects to mongodb")
    
    try:
        operations = []
        for project in completed_projects:
            operation = UpdateOne(
                {"title": project["title"]}, 
                {"$set": project}, 
                upsert=True
            )
            operations.append(operation)
            
        if operations:
            result = collection_name.bulk_write(operations)
            print(f"Successfully saved! Inserted: {result.upserted_count}, Updated: {result.modified_count}")
    
    except Exception as e:
        print(f"Error saving to mongodb: {str(e)}")

    return state


def build_portfolio_agent():
    """Builds and compiles the SuperGraph"""
    graph = StateGraph(SuperGraphState)
    graph.add_node("fetch_all_repos_and_readmes",fetch_all_repos_and_readmes)
    graph.add_node("run_project_subgraph",run_project_subgraph)
    graph.add_node("save_projects",save_projects)

    graph.add_edge(START,"fetch_all_repos_and_readmes")
    graph.add_conditional_edges("fetch_all_repos_and_readmes",dispatch_sub_graph)
    graph.add_edge("run_project_subgraph","save_projects")
    graph.add_edge("save_projects",END)

    app = graph.compile()
    png_bytes = app.get_graph().draw_mermaid_png()
    with open("project_scanner.png","wb") as f:
        f.write(png_bytes)
    return app

if __name__ == "__main__":
    agent = build_portfolio_agent()
    agent.invoke({})