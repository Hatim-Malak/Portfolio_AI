from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from agents.github_project_scanner_agent import build_portfolio_agent
from agents.chatbot import build_chatbot_agent
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

@router.get("/chatbot/history/{session_id}")
def get_chat_history(session_id: str):
    """Fetches the previous messages for a user session."""
    agent = build_chatbot_agent()
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
    
    # 1. Accept the WebSocket connection from the frontend
    await websocket.accept()
    
    # 2. Initialize the agent and the specific user's config
    agent = build_chatbot_agent()
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
                    
                    # Send the JSON payload back to your React frontend
                    await websocket.send_json({
                        "role": "ai",
                        "content": ai_message,
                        "route": route_decision
                    })
                    
    except WebSocketDisconnect:
        # The user closed the browser or disconnected
        print(f"User {session_id} disconnected from WebSocket.")