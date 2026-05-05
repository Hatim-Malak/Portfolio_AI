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


load_dotenv()

github_token = os.getenv("GITHUB_API")
llm = ChatGroq(model="llama-3.1-8b-instant",temperature=0.5)

class SubGraphState(TypedDict):
    title:str
    readme:str
    description:str
    languages:dict
    mobile_url:str
    desktop_url:str

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
        result = detail_llm.invoke(formatted_message)
        
        return {
            "description":result.description,
            "languages":result.languages
        }
    
    def image_generator(state:SubGraphState) -> dict:
        refined_prompt = (
            f"Isometric 3D tech illustration of {state["description"]}, "
            f"featuring a clean dashboard UI, glowing data nodes, "
            f"frosted glass texture (glassmorphism), high-tech digital interface, "
            f"minimalist workspace background, vibrant blue accents on a dark theme, "
            f"4k resolution, Unreal Engine 5 render style, professional SaaS product aesthetic"
        )
        encoded_prompt = requests.utils.quote(refined_prompt)
        
        dims = {
        "desktop": (1920, 1080),
        "mobile": (1080, 1920)
        }
        updates = {}

        for view_name, (w, h) in dims.items():
            api_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={w}&height={h}&nologo=true&seed={os.urandom(4).hex()}"
            
            print(f"Fetching {view_name} view...")
            time = 30
            if(view_name == "desktop"):
                time = 30
            else:
                time = 90
            
            try:
                response = requests.get(api_url, timeout=time)
                if response.status_code == 200:
                    url = upload_bytes_to_cloudinary(response.content)
                    if url:
                        updates[f"{view_name}_url"] = url
                        print(f"✅ Uploaded {view_name}")
                else:
                    print(f"❌ Pollinations failed: {response.status_code}")
            except Exception as e:
                print(f"⚠️ Error during {view_name} request: {e}")
        
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
        g = Github(github_token)
        user = g.get_user()
        
        repos = user.get_repos()
        ls = []
        for repo in repos:
            for project in projects:
                if repo.name == project["title"] or repo.updated_at == project["updated_at"]:
                    continue
                  
                print(f"--- Processing: {repo.full_name} ---")
                try:
                    readme = repo.get_readme()
                    readme_content = base64.b64decode(readme.content).decode('utf-8')
                    
                    project_data = {
                        "title": repo.name,                        
                        "readme": readme_content
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
        Send("run_project_subgraph",{"title":detail["title"],"readme":detail["readme"]}) for detail in state["details"] 
    ]

def save_projects(state:SuperGraphState) -> dict:
    """Takes the aggregated list of project and save it to mongodb"""
    completed_projects = state.get("projects",[])
    
    if not completed_projects:
        print("No new project to save")
        return state
    
    print(f"Preparing project to save {len(completed_projects)} projects to mongodb")
    
    try:
        collection_name.insert_many(completed_projects)
        print("Successfully savced all the projects to mongodb")
    
    except Exception as e:
        print(f"Error saving to mongodb: {str(e)}")

    return state



graph = StateGraph(SuperGraphState)
graph.add_node("fetch_all_repos_and_readmes",fetch_all_repos_and_readmes)
graph.add_node("run_project_subgraph",run_project_subgraph)
graph.add_node("save_projects",save_projects)

graph.add_edge(START,"fetch_all_repos_and_readmes")
graph.add_conditional_edges("fetch_all_repos_and_readmes",dispatch_sub_graph)
graph.add_edge("run_project_subgraph","save_projects")
graph.add_edge("save_projects",END)
