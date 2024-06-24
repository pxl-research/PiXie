from abc import ABC, abstractmethod
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


class Splitter(ABC):
    """
    Abstract base class for a text splitter.
    """

    @abstractmethod
    def split(self, doc):
        """
        Abstract method to split a text document into chunks.
        """
        pass


class CustomMarkdownSplitter(Splitter):
    """
    Splitter for markdown documents.
    """

    def __init__(self, header_depth, chunk_size, chunk_overlap):
        """
        Initialize the splitter with the header depth and chunk size.
        """
        self.headers_to_split_on = [("#" * header_depth, f"Header {header_depth}")]
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, docs: List[Document]) -> List[Document]:
        """
        Split a markdown document into chunks based on headers and character count.
        """
        combined_text = ""
        for document in docs:
            combined_text += document.page_content

        md_header_text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on
        )
        md_header_splits = md_header_text_splitter.split_text(combined_text)

        rec_char_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        splits = rec_char_text_splitter.split_documents(md_header_splits)
        return splits
