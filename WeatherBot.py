import os
import json
import requests
from dotenv import load_dotenv
from groq import Groq
import streamlit as st

LLM = "Groq"

# Load values from .env to environment
load_dotenv()
OPENWEATHER_API_KEY = os.environ['OPENWEATHER_API_KEY']

class GroqWeatherBot:
    def __init__(self, apiKey):

        # init groqClient
        client = Groq(api_key=apiKey)

        self.client = client

    def get_current_weather(self, location, unit="celsius"):
        """Get the current weather in a given location"""

        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        complete_url = f"{base_url}appid={OPENWEATHER_API_KEY}&q={location}"

        response = requests.get(complete_url)

        if response.status_code == 200:
            data = response.json()
            weather = data['weather'][0]['main']
            temperature = data['main']['temp'] - 273.15  # Convert Kelvin to Celsius
            return json.dumps({
                "city": location,
                "weather": weather,
                "temperature": round(temperature, 2)
            })
        else:
            return json.dumps({"city": location, "weather": "Data Fetch Error", "temperature": "N/A"})

    def genResponseForUserPrompt(self, userPrompt):
        _model = "llama3-70b-8192"  # "llama3-70b-8192" "mixtral-8x7b-32768"
        client = self.client

        # define a function as tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"]},
                        },
                        "required": ["location"],
                    },
                },
            }
        ]

        messages = [
            {
                "role": "system",
                "content": "Your are a bot, who gives weather information. Keep your answers short to one or two lines. Add information on kind of clothes to wear, what to avoid etc. when telling about the weather info",
            },
            {
                "role": "user",
                "content": userPrompt,
            }
        ]

        # Query LLM with tool calls mentioned # Call 01 to LLM
        response = client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=0,
            max_tokens=300,
            tools=tools,
            tool_choice="auto"
        )

        # Call function for any tool calls
        groq_response = response.choices[0].message
        if groq_response.tool_calls:
            messages.append(groq_response)

            # For each tool call generate response
            for tool_call in groq_response.tool_calls:
                # Fetch function argument from toolCall
                func_args = json.loads(tool_call.function.arguments)
                # print(func_args)

                # Call Function
                func_resp = self.get_current_weather(**func_args)
                # print(f"func_output: {func_resp}")

                # Extend the conversation with function response
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": func_resp,
                    }
                )

        # Call 02 to LLM
        secondResp = client.chat.completions.create(
            model=_model,
            messages=messages
        )

        print(f"{secondResp=}")
        print(f"\n\n{secondResp.choices[0].message.content}")

        return secondResp.choices[0].message.content


with st.sidebar:
    api_key = st.text_input(f"{LLM} API Key", key="chatbot_api_key", type="password")


st.title("💬 Weather Bot")
st.caption("🚀 powered by LLM")

# Initialize chat session with a welcome message
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Hi, I am your weather bot. How can I help you?"}]

# Display all messages of chat session till now
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Prompt user for input
if prompt := st.chat_input():
    if not api_key:
        st.info(f"Please add your {LLM} API key to continue.")
        st.stop()

    # Display and record user input in chat session
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Lazy Init groq weather bot
    if "groqWB" not in st.session_state:
        groqWB = GroqWeatherBot(api_key)
        st.session_state["groqWB"] = groqWB

    # Get response from weather bot
    groqWB = st.session_state["groqWB"]
    botResp = groqWB.genResponseForUserPrompt(prompt)

    st.session_state.messages.append({"role": "assistant", "content": botResp})
    st.chat_message("assistant").write(botResp)