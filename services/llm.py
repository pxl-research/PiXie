from langchain_openai import AzureChatOpenAI
import os


class LLM:
    def __init__(self, model_name, background_color):
        self.model_name = model_name
        self.background_color = background_color


class GPT35(LLM):
    def __init__(self, temperature):
        super().__init__("gpt-3.5-turbo", "#c0c0c0")

        azure_openai_api_version = os.environ["AZURE_OPENAI_API_VERSION"]
        azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        openai_api_key = os.environ["AZURE_OPENAI_API_KEY"]

        self.model = AzureChatOpenAI(
            openai_api_version=azure_openai_api_version,
            azure_endpoint=azure_endpoint,
            openai_api_key=openai_api_key,
            azure_deployment="gpt35",
            temperature=temperature,
            verbose=True,
        )


class GPT4(LLM):
    def __init__(self, temperature):
        super().__init__("gpt-4", "#ffd700")

        azure_openai_api_version = os.environ["AZURE_OPENAI_API_VERSION"]
        azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT_GPT4"]
        openai_api_key = os.environ["AZURE_OPENAI_API_KEY_GPT4"]

        self.model = AzureChatOpenAI(
            openai_api_version=azure_openai_api_version,
            azure_endpoint=azure_endpoint,
            openai_api_key=openai_api_key,
            azure_deployment="gpt4",
            temperature=temperature,
        )
