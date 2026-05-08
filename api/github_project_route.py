from fastapi import APIRouter
from agents.github_project_scanner_agent import build_portfolio_agent
from schemas.schema import list_serial
from config.database import collection_name

router = APIRouter(prefix="/projects",tags=["projects"])

@router.get("/agent")
def get_projects():
    agent = build_portfolio_agent()
    result =  agent.invoke({})
    todos = list_serial(collection_name.find())
    return todos