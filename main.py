from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.github_project_route import router
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI()

# Define the origins that are allowed to make requests to this API
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://hatim-porfolio.vercel.app"
]

# Add the CORS middleware to your FastAPI application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # List of allowed origins
    allow_credentials=True,      # Allow cookies/authorization headers
    allow_methods=["*"],         # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],         # Allow all headers
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)