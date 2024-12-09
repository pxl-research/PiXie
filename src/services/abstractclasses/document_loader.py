import csv
import logging
import os
from abc import ABC, abstractmethod
from langchain.schema import Document
from pathlib import Path
from typing import Union
from enum import Enum

import pandas as pd
import pypandoc


class DocumentFileType(Enum):
    Document = 0
    TabularDocument = 1
    Other = 2


def get_document_extensions() -> set[str]:
    return {".doc", ".docx", ".rtf", ".pdf", ".txt", ".md", ".pptx"}


def get_spreadsheet_extensions() -> set[str]:
    return {".xls", ".xlsx", ".xlsm", ".xlsb", ".odf", ".ods", ".odt"}


def get_tabular_extensions() -> set[str]:
    return get_spreadsheet_extensions() | {".csv"}


def get_document_file_type(file_name: str) -> DocumentFileType:
    base, extension = os.path.splitext(file_name)

    document_extensions = get_document_extensions()
    tabular_document_extensions = get_tabular_extensions()
    if extension in document_extensions:
        return DocumentFileType.Document
    elif extension in tabular_document_extensions:
        return DocumentFileType.TabularDocument
    return DocumentFileType.Other


class DocumentLoader(ABC):
    def load_document(
        self, file_path: str
    ) -> tuple[
        DocumentFileType, Union[list[Document], pd.DataFrame, dict[str, pd.DataFrame]]
    ]:
        path = Path(file_path)
        if not path.is_file():
            logging.error(f"{file_path} does not exist or is not a file.")
            raise FileNotFoundError(f"{file_path} does not exist or is not a file.")

        extension = path.suffix.lower()
        document_file_type = get_document_file_type(path.name)

        if extension == ".pdf":
            return document_file_type, self.load_pdf(file_path)
        elif extension == ".docx":
            return document_file_type, self.load_docx(file_path)
        elif extension == ".md":
            return document_file_type, self.load_md(file_path)
        elif extension == ".pptx":
            return document_file_type, self.load_pptx(file_path)
        elif extension == ".csv":
            return document_file_type, self.load_csv(file_path)
        elif extension in get_spreadsheet_extensions():
            return document_file_type, self.load_excel(file_path)
        else:
            logging.error(f"File type {extension} not supported.")
            raise ValueError("File type not supported")

    def load_docx(self, file_path: str) -> list[Document]:
        """
        Load a .docx file and convert it to markdown.

        Args:
            file_path (str): The path to the .docx file.

        Returns:
            list[Document]: A list containing the Document object.
        """
        docs = pypandoc.convert_file(file_path, "md")
        document = [Document(page_content=docs)]
        return document

    def load_md(self, file_path: str) -> list[Document]:
        """
        Load a markdown (.md) file.

        Args:
            file_path (str): The path to the .md file.

        Returns:
            list[Document]: A list containing the Document object.
        """
        if not os.path.isfile(file_path):
            logging.error(f"{file_path} does not exist or is not a file.")
            return
        with open(file_path, "r") as file:
            docs = file.read()
        document = [Document(page_content=docs)]
        return document

    @abstractmethod
    def load_pdf(self, file_path: str) -> list[Document]:
        """
        Abstract method to load a PDF file.

        Args:
            file_path (str): The path to the PDF file.

        Returns:
            list[Document]: A list of Document objects.
        """
        pass

    def load_pptx(self, file_path: str) -> list[Document]:
        """
        Abstract method to load a Powerpoint file.

        Args:
            file_path (str): The path to the Powerpoint file.

        Returns:
            list[Document]: A list of Document objects.
        """
        pass

    def load_csv(self, file_path: str) -> pd.DataFrame:
        """
        Load a CSV (.csv) file.

        Args:
            file_path (str): The path to the .csv file.

        Returns:
            pd.DataFrame: Pandas DataFrame containing the content of the CSV file.
        """

        def _detect_csv_delimiter(file_path: str) -> str:
            delimiter = ","
            with open(file_path, "r") as file:
                sample = file.read(1024)  # Read the first 1KB for detection
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            return delimiter

        try:
            delimiter = _detect_csv_delimiter(file_path)

            # Try reading with the default header and
            # check if the first row has valid header-like strings
            df = pd.read_csv(file_path, header="infer", sep=delimiter)
            if not df.columns.to_series().apply(lambda x: isinstance(x, str)).all():
                # Reset to default column names if headers are invalid
                df = pd.read_csv(file_path, header=None, sep=",")
                df.columns = [f"col_{i}" for i in range(df.shape[1])]
        except pd.errors.ParserError:
            # If parsing fails, assume no header
            df = pd.read_csv(file_path, header=None, sep=delimiter)
            df.columns = [f"col_{i}" for i in range(df.shape[1])]
        except Exception as e:
            logging.error(f"Cannot read file '{file_path}'. Error: {str(e)}")
        return df

    def load_excel(self, file_path: str) -> dict[str, pd.DataFrame]:
        """
        Load an Excel (.xls, .xlsx, .xlsm, .xlsb, .odf, .ods, .odt) file.

        Args:
            file_path (str): The path to the Excel file.

        Returns:
            dict[str, pd.DataFrame]: A dictionary containing a key (sheet_name)
                and value (the table as a pd.DataFrame), since a spreadsheet has multiple tables.
        """
        all_sheets: dict[str, pd.DataFrame] = pd.read_excel(
            file_path, sheet_name=None, header=None
        )
        processed_sheets: dict[str, pd.DataFrame] = {}

        for sheet_name, df in all_sheets.items():
            if not df.iloc[0].apply(lambda x: isinstance(x, str)).all():
                # No valid header; set default column names
                df.columns = [f"col_{i}" for i in range(df.shape[1])]
            else:
                # Valid header: Use the first row as header
                df.columns = df.iloc[0]

            df = df[1:].reset_index(drop=True)
            processed_sheets[sheet_name] = df

        return processed_sheets
