from pydantic import BaseModel

class Project(BaseModel):
    title:str   
    readme:str
    description:str
    languages:dict
    mobile_url:str
    desktop_url:str
    updated_at:str