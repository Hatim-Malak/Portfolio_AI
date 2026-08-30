import email
from pydantic._internal._known_annotated_metadata import SET_CONSTRAINTS
from datetime import datetime,timedelta,timezone

from fastapi import Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError,jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from config.database import collection_user_name

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated = "auto"
)

def hash_password(password:str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password:str,hashed_password:str) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password
    )

def create_access_token(data:dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp":expire
    })

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/login"
)

async def get_current_user(
    token:str = Depends(oauth2_scheme)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate credentials",
        headers = {"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        
        email = payload.get("sub")
        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception


    user = collection_user_name.find_one({
        "email": email
    })

    if user is None:
        raise credentials_exception

    return user
