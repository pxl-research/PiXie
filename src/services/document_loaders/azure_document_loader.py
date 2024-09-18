from typing import List
from langchain.schema import Document
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader
from services.abstractclasses.document_loader import DocumentLoader


class AzureDocumentLoader(DocumentLoader):
    """
    A document loader that uses Azure AI Document Intelligence to load and parse PDF files.
    """

    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        api_version: str = "2024-02-29-preview",
        api_model: str = "prebuilt-layout",
    ):
        """
        Initializes the AzureDocumentLoader with the necessary API credentials and parameters.

        Args:
            api_endpoint (str): The Azure AI Document Intelligence API endpoint.
            api_key (str): The Azure AI Document Intelligence API key.
            api_version (str): The API version to use.
            api_model (str): The API model to use for document parsing.
        """
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.api_model = api_model

    def load_pdf(self, file_path: str) -> List[Document]:
        """
        Loads a PDF file using Azure AI Document Intelligence and returns the parsed content.

        Args:
            file_path (str): The path to the PDF file.

        Returns:
            List[Document]: A list of Document objects containing the parsed content.
        """

        self.loader = AzureAIDocumentIntelligenceLoader(
            file_path=file_path,
            api_key=self.api_key,
            api_endpoint=self.api_endpoint,
            api_version=self.api_version,
            api_model=self.api_model,
            mode="markdown",
        )
        docs = self.loader.load()

        return docs
    
    def load_pptx(self, file_path: str) -> List[Document]:
        """
        Loads a Powerpoint file using Azure AI Document Intelligence and returns the parsed content.

        Args:
            file_path (str): The path to the Powerpoint file.

        Returns:
            List[Document]: A list of Document objects containing the parsed content.
        """

        self.loader = AzureAIDocumentIntelligenceLoader(
            file_path=file_path,
            api_key=self.api_key,
            api_endpoint=self.api_endpoint,
            api_version=self.api_version,
            api_model=self.api_model,
            mode="markdown",
        )
        docs = self.loader.load()

        return docs
