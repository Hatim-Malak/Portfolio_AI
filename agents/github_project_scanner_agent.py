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
from langchain_text_splitters import RecursiveCharacterTextSplitter
from schemas.schema import list_serial
from langgraph.types import Send
from typing import Literal
from pymongo import UpdateOne
import time
import threading
import json
load_dotenv()

cf_lock = threading.Lock()
github_token = os.getenv("GITHUB_API")
llm = ChatGroq(model="qwen/qwen3.8-27b", temperature=0.5)

class SubGraphState(TypedDict):
    title:str
    readme:str
    description:str
    languages:dict
    mobile_url:str
    desktop_url:str
    updated_at: str
    github_link:str
    live_link:str

class SuperGraphState(TypedDict):
    details:Annotated[list[dict],operator.add]
    projects:Annotated[list[SubGraphState],operator.add]
    route:Literal["subGraph","end"]
    
def subGraph() -> StateGraph:
    
    def detail_generator(state:SubGraphState) -> dict:
        """It generate the description and what languages used through analysing readme of the project"""
        
        raw_readme = state.get("readme","")
        
        MAX_SAFE_LENGTH = 15000
        
        if len(raw_readme) > MAX_SAFE_LENGTH:
            print(f"README too large ({len(raw_readme)} chars). Initiating Map-Reduce...")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=8000,
                chunk_overlap=500,
            )
            
            chunks = text_splitter.split_text(raw_readme)
            
            map_prompt = ChatPromptTemplate.from_template(
                "Extract the core features, problems solved, and any programming languages/tools mentioned in this README chunk:\n\n{chunk}"
            )
            
            mapped_summaries = []
            for i, chunk in enumerate(chunks):
                formatted_map = map_prompt.format_messages(chunk=chunk)
                
                chunk_result = None
                for attempt in range(5):
                    try:
                        chunk_result = llm.invoke(formatted_map)
                        break
                    except Exception as e:
                        if "429" in str(e) or "rate_limit" in str(e).lower():
                            wait_time = 15 * (2 ** attempt)  # Exponential backoff: 15s, 30s, 60s, 120s, 240s (free tier)
                            print(f"Rate limit hit on chunk {i+1}/{len(chunks)} for {state['title']}. Waiting {wait_time}s... (Attempt {attempt+1}/5)")
                            time.sleep(wait_time)
                        else:
                            raise e
                
                if chunk_result:
                    mapped_summaries.append(chunk_result.content)
                    time.sleep(3)  # 3-second delay between chunks for free tier
            processed_readme_context = "\n\n--- Next Chunk Summary ---\n\n".join(mapped_summaries)
        else:
            processed_readme_context = raw_readme
               
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
            Return your response in valid JSON with these keys:
            {{"description": "...", "languages": {{...}}}}"""
        ),
        (
            "human", 
            "Analyze the following README content and extract the details:\n\n{readme}"
        )
        ])
        formatted_message = prompt.format_messages(readme=processed_readme_context)
        result = None
        for attempt in range(5): 
            try:
                result = llm.invoke(formatted_message)
                break 
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait_time = 15 * (2 ** attempt)  # Exponential backoff: 15s, 30s, 60s, 120s, 240s (free tier)
                    print(f"Groq Rate Limit hit for {state['title']}. Waiting {wait_time}s... (Attempt {attempt+1}/5)")
                    time.sleep(wait_time)
                else:
                    print(f"Groq error: {e}")
                    raise e 
                    
        if not result:
            return {"description": "Description generation failed.", "languages": {}}
        
        # Parse JSON response manually
        try:
            content = result.content
            
            # Handle markdown code blocks (```json...```)
            if "```json" in content:
                # Extract JSON from markdown code block
                start_idx = content.find("```json") + 7
                end_idx = content.find("```", start_idx)
                if end_idx != -1:
                    content = content[start_idx:end_idx].strip()
            elif "```" in content:
                # Extract from generic code block
                start_idx = content.find("```") + 3
                end_idx = content.find("```", start_idx)
                if end_idx != -1:
                    content = content[start_idx:end_idx].strip()
            
            parsed = json.loads(content)
            description = parsed.get("description", "")
            languages = parsed.get("languages", {})
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON for {state['title']}. Raw response: {content}")
            return {"description": "Failed to parse response.", "languages": {}}
        
        return {
            "description": description,
            "languages": languages
        }
    
    def image_generator(state:SubGraphState) -> dict:
        refined_prompt = (
            f"A beautiful, high-resolution UI/UX mockup of a SaaS web application for: {state['description']}. "
            f"The interface features a dark mode theme with glowing neon blue and purple accents. "
            f"It has frosted glassmorphism panels, clean typography, and a professional Dribbble portfolio aesthetic. "
            f"Displayed in 3D isometric perspective."
        )
        
        API_URL = os.getenv("CLOUDFLARE_WORKER_URL")
        
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
                            print(f"Successfully uploaded {view_name} for {state['title']}")
                            break 
                    else:
                        print(f"Worker Error {response.status_code}: {response.text}")
                        time.sleep(5)
                        
                except Exception as e:
                    print(f"Request failed: {str(e)}")
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
        ignore_repo = ["Hatim-Malak","Spring-boot-demo","spring_security","lunaris2.0","lunaris","admin-dashboard"]
        existing_projects_map = {p["title"]: str(p.get("updated_at")) for p in projects}
        g = Github(github_token)
        user = g.get_user()    
        repos = user.get_repos()
        ls = []
        for repo in repos:
            if len(ls) >= 5:
                print("\nReached batch limit of 5 projects. Stopping fetch for this run.")
                break
            if repo.fork:
                continue
            repo_updated_str = str(repo.updated_at)
            if repo.name in ignore_repo:
                collection_name.delete_one({"title":repo.name})
                continue
            
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
                github_link = repo.html_url
                live_link = repo.homepage
    
                project_data = {
                    "title": repo.name,                        
                    "readme": readme_content,
                    "updated_at":repo_updated_str,
                    "github_link":github_link,
                    "live_link":live_link,
                }
                ls.append(project_data)
                print(f"Successfully fetched data for {repo.name}")
                print(readme_content)
            
            except Exception:
                print(f"No README found for {repo.name}, skipping...")
                collection_name.delete_one({"title": repo.name})
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
        return {"route": "end"}
        
def dispatch_sub_graph(state:SuperGraphState) -> list[Send]:
    """Dynamically create parallel subgraph task using send api"""
    if state.get("route") == "end":
        return END
    return [
        Send("run_project_subgraph",{"title":detail["title"],"readme":detail["readme"],"updated_at":detail["updated_at"],"github_link":detail["github_link"],"live_link":detail["live_link"]}) for detail in state["details"] 
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