from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Depends, UploadFile, File, Form
from langchain_core.messages import HumanMessage
from agents.github_project_scanner_agent import build_portfolio_agent
from agents.chatbot import build_chatbot_agent
from schemas.schema import list_serial, individual_serial
from config.database import collection_name
from slowapi import Limiter
from fastapi import Request
from slowapi.util import get_remote_address
from config.rate_limiter import limiter
from models.project import ProjectUpdate
from bson import ObjectId
from bson.errors import InvalidId
from config.auth import get_current_user, get_current_admin
from config.cloudinary import upload_fastapi_file
import os
import asyncio
import io
from PIL import Image, UnidentifiedImageError

# Simple in-memory connection tracker for WebSockets
active_ws_connections: dict[str, int] = {}
WS_MAX_CONNECTIONS_PER_IP = 5

router = APIRouter(prefix="/projects",tags=["projects"])

@router.put("/{project_id}")
def update_project(
    project_id: str, 
    project_update: ProjectUpdate,
    current_user: dict = Depends(get_current_admin)
):
    try:
        obj_id = ObjectId(project_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    update_data = {k: v for k, v in project_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
        
    result = collection_name.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
        
    updated_project = collection_name.find_one({"_id": obj_id})
    return individual_serial(updated_project)

@router.delete("/{project_id}")
def delete_project(
    project_id: str, 
    current_user: dict = Depends(get_current_admin)
):
    try:
        obj_id = ObjectId(project_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
        
    result = collection_name.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return {"message": "Project deleted successfully"}

@router.post("/{project_id}/media")
@limiter.limit("5/minute")
async def upload_project_media(
    request: Request,
    project_id: str,
    file: UploadFile = File(...),
    field_type: str = Form(...),
    current_user: dict = Depends(get_current_admin)
):
    try:
        obj_id = ObjectId(project_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
        
    project = collection_name.find_one({"_id": obj_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if field_type not in ["mobile_url", "desktop_url"]:
        raise HTTPException(status_code=400, detail="field_type must be 'mobile_url' or 'desktop_url'. Videos should be uploaded to YouTube and linked via the update route.")

    # Validate file size (max 10MB)
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Max 10MB allowed.")

    # Validate actual image bytes
    try:
        file_bytes = await file.read()
        image = Image.open(io.BytesIO(file_bytes))
        image.verify()
        if image.format not in ["JPEG", "PNG", "WEBP", "MPO"]:
            raise HTTPException(status_code=400, detail=f"Unsupported image format: {image.format}. Allowed: JPEG, PNG, WEBP.")
        
        # Reset file pointer for Cloudinary upload
        file.file.seek(0)
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Invalid image file bytes.")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail="Error validating image.")

    # Upload to Cloudinary
    url = await upload_fastapi_file(file)
    if not url:
        raise HTTPException(status_code=500, detail="Failed to upload file to Cloudinary")

    # Update database
    if field_type == "mobile_url":
        collection_name.update_one({"_id": obj_id}, {"$push": {"mobile_url": url}})
    elif field_type == "desktop_url":
        collection_name.update_one({"_id": obj_id}, {"$push": {"desktop_url": url}})

    updated_project = collection_name.find_one({"_id": obj_id})
    return individual_serial(updated_project)

@router.get("/")
@limiter.limit("30/minute")
def get_all_projects(request: Request):
    """Instantly fetches all projects from the database."""
    projects = list_serial(collection_name.find())
    return projects

@router.post("/agent")
@limiter.limit("1/5 minute")
def post_projects_agent(request: Request):
    """Triggers the GitHub scanner agent and then returns projects."""
    agent = request.app.state.portfolio_agent
    # Run the graph synchronously inside a separate thread to prevent blocking
    # Using asyncio.run inside to_thread doesn't work if it's already async, 
    # but agent.invoke is sync so it blocks. Let's just call it. Wait, the endpoint is NOT async def, 
    # so FastAPI runs it in a threadpool natively!
    agent.invoke({})
    todos = list_serial(collection_name.find())
    return todos

@router.get("/chatbot/history/{session_id}")
def get_chat_history(request: Request, session_id: str):
    """Fetches the previous messages for a user session."""
    agent = request.app.state.chatbot_agent
    config = {"configurable": {"thread_id": session_id}}
    
    current_state = agent.get_state(config=config)
    history = []
    
    if current_state and "messages" in current_state.values:
        for msg in current_state.values["messages"]:
            # Format it nicely for your frontend
            history.append({
                "role": msg.type, # will be 'human' or 'ai'
                "content": msg.content
            })
            
    return {"session_id": session_id, "history": history}


@router.websocket("/chatbot/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """Handles real-time bi-directional chat over WebSockets."""
    client_ip = websocket.client.host if websocket.client else "unknown"
    origin = websocket.headers.get("origin")
    allowed_origin = os.getenv("ALLOWED_ORIGIN")
    
    if origin and allowed_origin and origin != allowed_origin:
        print(f"Rejected WS connection from unallowed origin: {origin}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Check connection limits
    current_connections = active_ws_connections.get(client_ip, 0)
    if current_connections >= WS_MAX_CONNECTIONS_PER_IP:
        print(f"Rejected WS connection from {client_ip} due to rate limiting")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 1. Accept the WebSocket connection from the frontend
    await websocket.accept()
    active_ws_connections[client_ip] = current_connections + 1
    
    # 2. Initialize the agent and the specific user's config
    agent = websocket.app.state.chatbot_agent
    config = {"configurable": {"thread_id": session_id}}

    try:
        # Keep the connection open and listen for messages
        while True:
            # Wait for the user to send a message
            user_input = await websocket.receive_text()
            
            # Construct the input for your graph
            graph_input = {
                "query": user_input,
                "messages": [HumanMessage(content=user_input)]
            }
            
            # Process through LangGraph asynchronously
            # .astream yields updates as each node finishes
            async for event in agent.astream(graph_input, config=config):
                
                # We only want to send data back to the user when the chat_model node is done
                if "chat_model" in event:
                    node_data = event["chat_model"]
                    ai_message = node_data["messages"][-1].content
                    route_decision = node_data.get("route", "None")
                    
                    await websocket.send_json({
                        "role": "ai",
                        "content": ai_message,
                        "route": route_decision
                    })
                    
    except WebSocketDisconnect:
        # The user closed the browser or disconnected
        print(f"User {session_id} disconnected from WebSocket.")
    finally:
        if client_ip in active_ws_connections:
            active_ws_connections[client_ip] -= 1
            if active_ws_connections[client_ip] <= 0:
                del active_ws_connections[client_ip]