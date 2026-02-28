from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(
    model="gemini-3.1-pro-preview",
    api_key="AQ.Ab8RN6I_N-tP_sOSbHNsNwvwfBqqIsQ6VxXJX29Ad1YuXG1TTQ",
    vertexai=True,
)

# Call the Gemini 3.1 Pro Preview model
response = model.invoke(
    """
    Fill out this json; numbers are in millions; i already filled out first row:
        {"name": "Oil & Gas Drilling", "sizes": [151700, 161400, 171700, 182700]},
        {"name": "Oil & Gas Equipment & Services", "sizes": []},
        {"name": "Integrated Oil & Gas", "sizes": []},
        {"name": "Oil & Gas Exploration & Production", "sizes": []},
        {"name": "Oil & Gas Refining & Marketing", "sizes": []},
        {"name": "Oil & Gas Storage & Transportation", "sizes": []},
        {"name": "Coal & Consumable Fuels", "sizes": []}
    """,
)

print(response)
