import os
from langchain_openai import AzureChatOpenAI
from services.abstractclasses.llm import LLM


class AzureOpenAILLM(LLM):
    """
    Azure OpenAI implementation of the LLM class, supporting different GPT models.
    """

    def __init__(
        self,
        api_version: str,
        api_endpoint: str,
        api_key: str,
        model_version: str,
        temperature: float = 0.0,
    ):
        """
        Initialize the AzureOpenAILLM with the specified API parameters, model version, and temperature.

        Args:
            api_version (str): The version of the Azure OpenAI API to use.
            api_endpoint (str): The Azure OpenAI endpoint.
            api_key (str): The API key for authentication with Azure OpenAI.
            model_version (str): The version of GPT to use (e.g., "gpt-3.5-turbo", "gpt-4").
            temperature (float, optional): The temperature setting for the model. Defaults to 0.0.
        """
        super().__init__(model_version)

        self.model = AzureChatOpenAI(
            openai_api_version=api_version,
            azure_endpoint=api_endpoint,
            openai_api_key=api_key,
            azure_deployment=model_version,
            temperature=temperature,
            verbose=True,
        )
