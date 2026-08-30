from pydantic import BaseModel
from typing import Optional, List, Dict

class Project(BaseModel):
    title:str   
    readme:str
    description:str
    languages:dict
    mobile_url:str
    desktop_url:str
    updated_at:str
    github_link:str
    live_link:str
    video: Optional[str] = None
    gallery: Optional[List[str]] = None

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    readme: Optional[str] = None
    description: Optional[str] = None
    languages: Optional[Dict] = None
    mobile_url: Optional[str] = None
    desktop_url: Optional[str] = None
    updated_at: Optional[str] = None
    github_link: Optional[str] = None
    live_link: Optional[str] = None
    video: Optional[str] = None
    gallery: Optional[List[str]] = None