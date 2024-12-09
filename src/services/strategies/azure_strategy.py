from langchain.schema import Document
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader
from typing import List


class AzureStrategy:
    def __init__(self, api_endpoint: str, api_key: str):
        self.api_endpoint = api_endpoint
        self.api_key = api_key

    def process(self, file_path: str) -> List[Document]:
        loader = AzureAIDocumentIntelligenceLoader(
            file_path=file_path,
            api_key=self.api_key,
            api_endpoint=self.api_endpoint,
            mode="markdown",
        )
        return loader.load()
