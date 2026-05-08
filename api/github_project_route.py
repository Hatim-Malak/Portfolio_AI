from fastapi import APIRouter
from agents.github_project_scanner_agent import build_portfolio_agent
from schemas.schema import list_serial
from config.database import collection_name
from slowapi import Limiter
from fastapi import Request
from slowapi.util import get_remote_address
from config.rate_limiter import limiter

router = APIRouter(prefix="/projects",tags=["projects"])

@router.get("/agent")
@limiter.limit("1/5 minute")
def get_projects(request: Request):
    agent = build_portfolio_agent()
    agent.invoke({})
    todos = list_serial(collection_name.find())
    return todos