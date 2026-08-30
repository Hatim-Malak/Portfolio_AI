from pydantic import BaseModel


class User(BaseModel):
    email:str
    passwordHash:str
    role:str
    created_at:str
    updated_at:str
    