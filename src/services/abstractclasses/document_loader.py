import pypandoc
import logging
import os
from abc import ABC, abstractmethod
from langchain.schema import Document
from pathlib import Path
from typing import List


class DocumentLoader(ABC):
    """
    Abstract base class for loading different types of documents.
    """

    def load_document(self, file_path: str) -> List[Document]:
        """
        Load a document based on its file extension.

        Args:
            file_path (str): The path to the document file.

        Returns:
            List[Document]: A list of Document objects.

        Raises:
            ValueError: If the file type is not supported.
        """
        path = Path(file_path)
        if not path.is_file():
            logging.error(f"{file_path} does not exist or is not a file.")
            raise FileNotFoundError(f"{file_path} does not exist or is not a file.")

        extension = path.suffix.lower()

        if extension == ".pdf":
            return self.load_pdf(file_path)
        elif extension == ".docx":
            return self.load_docx(file_path)
        elif extension == ".md":
            return self.load_md(file_path)
        elif extension == ".pptx":
            return self.load_pptx(file_path)
        else:
            logging.error(f"File type {extension} not supported.")
            raise ValueError("File type not supported")

    def load_docx(self, file_path: str) -> List[Document]:
        """
        Load a .docx file and convert it to markdown.

        Args:
            file_path (str): The path to the .docx file.

        Returns:
            List[Document]: A list containing the Document object.
        """
        docs = pypandoc.convert_file(file_path, "md")
        document = [Document(page_content=docs)]
        return document

    def load_md(self, file_path: str) -> List[Document]:
        """
        Load a markdown (.md) file.

        Args:
            file_path (str): The path to the .md file.

        Returns:
            List[Document]: A list containing the Document object.
        """
        if not os.path.isfile(file_path):
            logging.error(f"{file_path} does not exist or is not a file.")
            return
        with open(file_path, "r") as file:
            docs = file.read()
        document = [Document(page_content=docs)]
        return document

    @abstractmethod
    def load_pdf(self, file_path: str) -> List[Document]:
        """
        Abstract method to load a PDF file.

        Args:
            file_path (str): The path to the PDF file.

        Returns:
            List[Document]: A list of Document objects.
        """
        pass

    @abstractmethod
    def load_pptx(self, file_path: str) -> List[Document]:
        """
        Abstract method to load a Powerpoint file.

        Args:
            file_path (str): The path to the Powerpoint file.

        Returns:
            List[Document]: A list of Document objects.
        """
        pass
