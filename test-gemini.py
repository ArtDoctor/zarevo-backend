from google import genai
from google.genai import types

# Initialize the client using your API key
client = genai.Client(
    vertexai=True,
    api_key="AQ.Ab8RN6I_N-tP_sOSbHNsNwvwfBqqIsQ6VxXJX29Ad1YuXG1TTQ"
)

# Define the generation configuration to control the model's thinking
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        # Available levels for Gemini 3.1 Pro: LOW, MEDIUM, HIGH
        thinking_level=types.ThinkingLevel.MEDIUM
    )
)

# Call the Gemini 3.1 Pro Preview model
response = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents="""
    Fill out this json; numbers are in millions; i already filled out first row:
        {"name": "Oil & Gas Drilling", "sizes": [151700, 161400, 171700, 182700]},
        {"name": "Oil & Gas Equipment & Services", "sizes": []},
        {"name": "Integrated Oil & Gas", "sizes": []},
        {"name": "Oil & Gas Exploration & Production", "sizes": []},
        {"name": "Oil & Gas Refining & Marketing", "sizes": []},
        {"name": "Oil & Gas Storage & Transportation", "sizes": []},
        {"name": "Coal & Consumable Fuels", "sizes": []}
    """,
    config=config
)

print(response.text)
