import os
from dotenv import load_dotenv
from typing import Dict, List
from langchain.schema import Document
from services.strategies.pandoc_strategy import PandocStrategy
from services.strategies.azure_strategy import AzureStrategy
from services.strategies.docling_strategy import DoclingStrategy

from services.abstractclasses.document_loader import DocumentFileType

load_dotenv()


class ConfigurableDocumentProcessingManager:
    def __init__(self, file_to_strategy: Dict[str, str]):
        self.file_to_strategy = file_to_strategy
        self.strategies = self._initialize_strategies()

    def _initialize_strategies(self) -> Dict[str, object]:
        return {
            "PANDOC": PandocStrategy(),
            "AZURE": AzureStrategy(
                api_endpoint=os.getenv("AZURE_API_ENDPOINT"),
                api_key=os.getenv("AZURE_API_KEY"),
            ),
            "DOCLING": DoclingStrategy(),
        }

    def load_document(self, file_path: str) -> tuple[DocumentFileType, List[Document]]:
        """Loads and processes a document using the appropriate strategy based on file extension.

        Args:
            file_path (str): Path to the document file to be processed.

        Returns:
            tuple[DocumentFileType, List[Document]]: A tuple containing:
                - DocumentFileType: Always returns DocumentFileType.DOCUMENT
                - List[Document]: List of processed Document objects

        Raises:
            ValueError: If no strategy is configured for the file extension
            ValueError: If the configured strategy is not found
        """
        file_extension = os.path.splitext(file_path)[1].lower().lstrip(".")

        if file_extension not in self.file_to_strategy:
            raise ValueError(
                f"No strategy configured for file extension: {file_extension}"
            )

        strategy_name = self.file_to_strategy[file_extension]
        if strategy_name not in self.strategies:
            raise ValueError(f"Strategy not found: {strategy_name}")

        strategy = self.strategies[strategy_name]
        # The return type is hardcoded as DocumentFileType.Document
        # to indicate that the processed file is always a document.
        return DocumentFileType.Document, strategy.process(file_path)
