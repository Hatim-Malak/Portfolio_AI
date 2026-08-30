from datetime import timedelta,datetime
from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from models.user import User