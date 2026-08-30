from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
import os
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import your router and the shared limiter
from api.github_project_route import router as project_router
from api.user_route import router as user_router
from config.rate_limiter import limiter
from agents.github_project_scanner_agent import build_portfolio_agent
from agents.chatbot import build_chatbot_agent

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing AI agents...")
    app.state.portfolio_agent = build_portfolio_agent()
    app.state.chatbot_agent = build_chatbot_agent()
    print("Agents initialized successfully.")
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok"}


# Attach the limiter to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origin = os.getenv("ALLOWED_ORIGIN")
if not allowed_origin:
    raise RuntimeError("ALLOWED_ORIGIN environment variable is missing. Check your .env file.")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    allowed_origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router)
app.include_router(user_router)

@app.get("/ping")
def keep_alive():
    return {"status": "I am awake!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)