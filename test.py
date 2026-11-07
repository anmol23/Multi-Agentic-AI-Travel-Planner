# from tools.tavily_tool import tavily_search

# result = tavily_search("Best hotels in india")

# print(result)


# from tools.flight_tool import search_flights

# print(search_flights("Plan a 7 days Japan trip"))

# import asyncio
# from mcp_client import get_all_tools
# if __name__=="__main__":
#     tools= asyncio.run(get_all_tools())
#     print(tools)



from backend import run_travel_agent

response = run_travel_agent(user_input="I want a 1 day trip to Bali, be very brief", thread_id="test")
print (response['answer']) 


# import asyncio
# from backend import tavily_agent

# async def main():

#     response = await tavily_agent.ainvoke({
#         "messages": [
#             ("user", "Find 2 budget hotels in Bali. Be brief.")
#         ]
#     })

#     print(response["messages"][-1].content)


# if __name__ == "__main__":
#     asyncio.run(main())

