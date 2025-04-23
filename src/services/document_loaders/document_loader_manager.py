import os
from typing import Union
from enum import Enum
from dotenv import load_dotenv

from langchain.schema import Document
import pandas as pd


from services.strategies.pandoc_strategy import PandocStrategy
from services.strategies.azure_strategy import AzureStrategy
from services.strategies.docling_strategy import DoclingStrategy
from services.strategies.pandas_csv_strategy import PandasCSVStrategy
from services.strategies.pandas_excel_strategy import PandasExcelStrategy
from services.strategies.markdown_strategy import MarkdownStrategy

load_dotenv()


class DocumentFileType(Enum):
    Document = 0
    TabularDocument = 1
    Other = 2


def get_document_extensions() -> set[str]:
    return {"doc", "docx", "odt", "rtf", "pdf", "pptx"}


def get_spreadsheet_extensions() -> set[str]:
    return {"xls", "xlsx", "ods"}


def get_tabular_extensions() -> set[str]:
    return get_spreadsheet_extensions() | {"csv"}


def get_document_file_type(file_path: str) -> DocumentFileType:

    # Remove sheet name if present (after #)
    base_file_path = file_path.split("#")[0]

    # Get extension from cleaned path
    extension = os.path.splitext(base_file_path)[1].lower().lstrip(".")
    document_extensions = get_document_extensions()
    tabular_document_extensions = get_tabular_extensions()
    if extension in document_extensions:
        return DocumentFileType.Document
    elif extension in tabular_document_extensions:
        return DocumentFileType.TabularDocument
    return DocumentFileType.Other


class ConfigurableDocumentProcessingManager:
    def __init__(self, file_to_strategy: dict[str, str]):
        self.file_to_strategy = file_to_strategy
        self.strategies = self._initialize_strategies()

    def _initialize_strategies(self) -> dict[str, object]:
        return {
            "PANDOC": PandocStrategy(),
            "AZURE": AzureStrategy(
                api_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
                api_key=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
            ),
            "DOCLING": DoclingStrategy(),
            "PANDAS_CSV": PandasCSVStrategy(),
            "PANDAS_EXCEL": PandasExcelStrategy(),
            "MARKDOWN": MarkdownStrategy(),
        }

    def load_document(
        self, file_path: str
    ) -> tuple[
        DocumentFileType, Union[list[Document], pd.DataFrame, dict[str, pd.DataFrame]]
    ]:
        """Loads and processes a document using the appropriate strategy based on file extension.

        Args:
            file_path (str): Path to the document file to be processed.

        Returns:
            tuple[DocumentFileType, Union[list[Document], pd.DataFrame, dict[str, pd.DataFrame]]]: A tuple containing:
                - DocumentFileType: Can be e.g. DocumentFileType.Document, DocumentFileType.TabularDocument, ...
                - Union[list[Document], pd.DataFrame, dict[str, pd.DataFrame]]: Can be a list of processed Document objects,
                    Pandas DataFrame or dictionary of Pandas DataFrame's (spreadsheets)

        Raises:
            ValueError: If no strategy is configured for the file extension
            ValueError: If the configured strategy is not found
        """
        file_extension = (
            os.path.splitext(file_path)[1].lower().lstrip(".")
        )  # e.g.: csv (no . )

        if file_extension not in self.file_to_strategy:
            raise ValueError(
                f"No strategy configured for file extension: {file_extension}"
            )

        strategy_name = self.file_to_strategy[file_extension]
        if strategy_name not in self.strategies:
            raise ValueError(f"Strategy not found: {strategy_name}")

        strategy = self.strategies[strategy_name]
        res = strategy.process(file_path)

        return get_document_file_type(file_path), res
