from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config.database import collection_resume
from config.auth import get_current_admin

router = APIRouter(prefix="/resume", tags=["resume"])

@router.get("/")
def get_resume():
    """Fetches the resume data."""
    resume = collection_resume.find_one({"_id": "main_resume"})
    if resume:
        resume.pop("_id", None)
        return resume
    return {}

@router.put("/")
def update_resume(resume_data: dict, current_user: dict = Depends(get_current_admin)):
    """Updates the resume data."""
    collection_resume.update_one(
        {"_id": "main_resume"},
        {"$set": resume_data},
        upsert=True
    )
    return {"message": "Resume updated successfully"}
