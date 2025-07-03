from conversation_loop import *
import os
from services.llms.azure_openai_llm import AzureOpenAILLM

llm = AzureOpenAILLM(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    model_version=os.getenv("AZURE_OPENAI_MODEL_VERSION")
)

# Create conversation_loop per new session
conversation_loop = ConversationLoop(llm=llm, collection_name="auva")
wait_for_user_input = True

while True:
    if not wait_for_user_input:
        break

    user_input = input("You: ").strip()

    if user_input.lower() == "stop":
        wait_for_user_input, ai_response = conversation_loop.send("stop")
        print("AI: " + ai_response)
        break

    wait_for_user_input, ai_response = conversation_loop.send(user_input)
    print("AI: " + ai_response)
