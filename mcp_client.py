import os
import sys
from pathlib import Path

import certifi
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain.chat_models import init_chat_model



load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")


llm = ChatGroq(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("GROQ_API_KEY"),    max_tokens=300

)


# ==========================================
# MCP client configuration
# ==========================================

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": (
                "https://mcp.tavily.com/mcp/"
                f"?tavilyApiKey={TAVILY_API_KEY}"
            )
        }
        # ,

        # "aviationstack": {
        #     "transport": "stdio",
        #     "command": "uvx",
        #     "args": [
        #         "aviationstack-mcp"
        #     ],
        #     "env": AVIATION_ENV
        # }
    }


)


# ==========================================
# Tavily MCP tool
# ==========================================


async def get_tavily_tools():

    tools = await client.get_tools(server_name="tavily")

    print("\nAvailable Tavily MCP tools:")

    for tool in tools:
        print(tool.name)

    return tools



# async def tavily_mcp_search(tool_name: str,  query: str):
#     await get_tavily_tools()


#     tool_to_invoke = search_tool.get(tool_name)

#     if tool_to_invoke is None:
#         available_tools = ", ".join(
#             sorted(search_tool.keys())
#         )

#         raise ValueError(
#             f"TAVILY tool '{tool_name}' "
#             "was not found. "
#             f"Available tools: "
#             f"{available_tools or 'none'}"
#         )

#     result = await tool_to_invoke.ainvoke(
#             {
#                 "query": query
#             }
#         )
#     return result




# # ==========================================
# # AviationStack MCP tools
# # ==========================================

# aviation_tools = {}


# async def initialize_aviation_tools():
#     global aviation_tools

#     if aviation_tools:
#         return

#     # Load only AviationStack.

#     tools = await client.get_tools(
#         server_name="aviationstack"
#     )

    #store all aviation tools
#     aviation_tools = {
#         tool.name: tool
#         for tool in tools
#     }

#     if not aviation_tools:
#         raise RuntimeError(
#             "AviationStack MCP connected but "
#             "returned no tools."
#         )


# async def aviation_mcp_call(
#     tool_name: str,   #passing which aviation tool to call within aviationstack mcp
#     tool_args: dict = None
# ):
#     await initialize_aviation_tools()


#     tool = aviation_tools.get(tool_name)

#     if tool is None:
#         available_tools = ", ".join(
#             sorted(aviation_tools.keys())
#         )

#         raise ValueError(
#             f"AviationStack tool '{tool_name}' "
#             "was not found. "
#             f"Available tools: "
#             f"{available_tools or 'none'}"
#         )

#     result = await tool.ainvoke(
#         tool_args or {}
#     )

#     return result






# ==========================================
# Destination extractor
# ==========================================

def extract_destination(query: str):
    prompt = f"""
    Extract only the destination city or country.

    Query:
    {query}

    Return only destination name.
    """

    response = llm.invoke(prompt)

    return response.content.strip()