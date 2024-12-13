import os
import logging
from langchain.schema import Document


class MarkdownStrategy:
    def process(self, file_path: str) -> list[Document]:
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
