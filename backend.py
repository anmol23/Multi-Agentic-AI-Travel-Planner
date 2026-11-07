import os 
import certifi
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from typing import TypedDict, Annotated, Any
import operator
import uuid
import asyncio
import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_groq import ChatGroq
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent



# from tools.tavily_tool import tavily_search

from tools.flight_tool import search_flights

from mcp_client import get_tavily_tools, extract_destination

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. Please add your Render PostgreSQL External Database URL to .env"
        )

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url


# GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# if not GROQ_API_KEY:
#     raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")


# =========================
# LLM
# =========================

llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("GROQ_API_KEY"),    max_tokens=300

)




# =========================
# State
# =========================

class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int
    weather_results: str



# =========================
# Hotel Agent using Tavily MCP
# =========================

# Create Tavily Agent
async def create_tavily_agent():

    # Get tools from Tavily MCP server
    tavily_tools = await get_tavily_tools()
    
  
    # Create agent with all available Tavily tools
    tavily_agent = create_react_agent(
        model=llm,
        tools=tavily_tools,
        prompt="""
        You are a web research agent.

        You have access to multiple Tavily tools.
        Choose the appropriate tool based on the user's query.
.
        2. Return only the 2 most relevant results.
        3. Keep each result under 100 words.
        4. Do not call multiple tools unless absolutely necessary.
        5. Do not use crawl or research for simple hotel searches.
        6. Provide a concise final answer.
        """,
        checkpointer=False
    )

    return tavily_agent


tavily_agent = asyncio.run(create_tavily_agent())


def hotel_agent(state: TravelState):

    query = f"Find the top 2 hotels for {state['user_query']}"

    response = asyncio.run(
        tavily_agent.ainvoke({
            "messages": [("user", query)]
        })
    )

    hotel_results = response["messages"][-1].content

    return {
        "hotel_results": hotel_results,
        "messages": [
            AIMessage(content="Hotel information fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }




# def hotel_agent(state: TravelState):
#     query = f"Top 2 hotels for {state['user_query']}"
    
#     #calling tavily search tool from mcp_search function defined in mcp client
#     hotel_results = asyncio.run(tavily_mcp_search("tavily_search",query))

#     return {
#         "hotel_results": hotel_results,
#         "messages": [
#             AIMessage(content="Hotel information fetched.")
#         ],
#         "llm_calls": state.get("llm_calls", 0) + 1
#     }



#=========================
#Flight Agent using defined tool
#=========================

def flight_agent(state: TravelState):
    query = state["user_query"]
    flight_data = search_flights(query)

    return {
        "flight_results": flight_data,
        "messages": [
            AIMessage(content="Flight results fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Flight Agent using Aviation Stack MCP
# =========================


# # Flight Tool Router Prompt
# FLIGHT_AGENT_PROMPT = """
# You are a travel flight expert.

# User Query:
# {query}

# Airport Information:
# {airport_data}

# Airline Information:
# {airline_data}

# Generate:

# 1. Likely departure airport
# 2. Likely arrival airport
# 3. Airlines serving this route
# 4. Typical flight duration
# 5. Estimated airfare range

# Return concise travel guidance.
# """



# # Flight Agent
# def flight_agent(state: TravelState):
#     print("\nINSIDE FLIGHT AGENT\n")

#     query = state["user_query"]

#     try:

#         airports = asyncio.run(
#             aviation_mcp_call(
#                 "list_airports"
#             )
#         )

#         airlines = asyncio.run(
#             aviation_mcp_call(
#                 "list_airlines"
#             )
#         )


#         print("\nAIRPORTS:", airports)
#         print("\nAIRLINES:", airlines)

#         prompt = FLIGHT_AGENT_PROMPT.format(
#             query=query,
#             airport_data=str(airports)[:3000],
#             airline_data=str(airlines)[:3000]
#         )

#         response = llm.invoke([
#             SystemMessage(
#                 content="You are an expert travel flight planner."
#             ),
#             HumanMessage(content=prompt)
#         ])

#         flight_data = response.content

#     except Exception as e:

#         flight_data = f"Flight information unavailable: {str(e)}"

#     return {
#         "flight_results": flight_data,
#         "messages": [
#             AIMessage(
#                 content="Flight recommendations generated"
#             )
#         ],
#         "llm_calls": state.get("llm_calls", 0) + 1
#     }








# =========================
# Itinerary Agent
# =========================

def itinerary_agent(state: TravelState):
    prompt = f"""
Create a complete travel itinerary.

User Query:
{state['user_query']}

Flight Results:
{state['flight_results']}

Hotel Results:
{state['hotel_results']}

Make the itinerary practical, budget-aware, and easy to follow.
"""

    response = llm.invoke([
        SystemMessage(content="You are an expert travel planner."),
        HumanMessage(content=prompt)
    ])

    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }



# =========================
# Final Response Agent
# =========================

def final_agent(state: TravelState):
    final_prompt = f"""
Generate the final travel response for the user.

User Request:
{state['user_query']}

Flights:
{state['flight_results']}

Hotels:
{state['hotel_results']}

Itinerary:
{state['itinerary']}

Format the final answer beautifully using these sections:

1. Flight Information 
2. Hotel Suggestions
3. Summary of itinary in very short

Important:
- Be clear and concise, in brief.
- Keep the response useful for real travel planning.
"""

    response = llm.invoke([
        SystemMessage(content="You are a professional AI travel booking assistant."),
        HumanMessage(content=final_prompt)
    ])

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# =========================
# Build Graph
# =========================

graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)


# =========================
# PostgreSQL Checkpointer
# =========================
DATABASE_URL = get_database_url()

_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row
)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)



# =========================
# Function for FastAPI
# =========================

def run_travel_agent(user_input: str, thread_id: str | None = None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = travel_graph.invoke(
        {
            "messages": [
                HumanMessage(content=user_input)
            ],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "llm_calls": 0
        },
        config=config
    )

    final_answer = result["messages"][-1].content

    if isinstance(final_answer, list):
        final_answer = "\n".join(
            item["text"]
            for item in final_answer
            if isinstance(item, dict) and item.get("type") == "text"
        )

    return {
        "thread_id": thread_id,
        "answer": final_answer,
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_calls": result.get("llm_calls", 0),
    }