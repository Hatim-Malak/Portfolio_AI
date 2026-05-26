from langgraph.graph import StateGraph,START,END
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from typing import Literal
from typing_extensions import Annotated,TypedDict
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage

load_dotenv()
llm = ChatGroq(model="llama-3.1-8b-instant",temperature=0.5)


def get_projects() -> list[dict]:
    