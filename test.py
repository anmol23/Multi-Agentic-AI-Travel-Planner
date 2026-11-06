# from tools.tavily_tool import tavily_search

# result = tavily_search("Best hotels in india")

# print(result)


# from tools.flight_tool import search_flights

# print(search_flights("Plan a 7 days Japan trip"))


from backend import run_travel_agent

response = run_travel_agent(user_input="I want a 5 days trip to Bali, make plan with budget of 60000", thread_id="test")
print (response['answer'])