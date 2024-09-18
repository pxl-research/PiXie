from services.abstractclasses.splitter import Splitter
from typing import List, Union
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


class CustomMarkdownSplitter(Splitter):
    """
    Splitter for markdown documents, splitting based on headers and character count.
    """

    def __init__(
        self, header_depth: Union[int, List[int]], chunk_size: int, chunk_overlap: int
    ):
        """
        Initialize the splitter with the header depth, chunk size, and chunk overlap.

        Args:
            header_depth (Union[int, List[int]]): The header depth(s) to split on.
            chunk_size (int): The maximum size of each chunk.
            chunk_overlap (int): The number of overlapping characters between chunks.
        """
        if isinstance(header_depth, int):
            header_depth = [header_depth]
        self.headers_to_split_on = [
            (f"{'#' * depth}", f"Header {depth}") for depth in header_depth
        ]

        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be 0 or greater")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, docs: List[Document]) -> List[Document]:
        """
        Split a list of markdown documents into chunks based on headers and character count.

        Args:
            docs (List[Document]): A list of documents to be split.

        Returns:
            List[Document]: A list of split document chunks.
        """
        combined_text = "".join([doc.page_content for doc in docs])

        md_header_text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on
        )
        md_header_splits = md_header_text_splitter.split_text(combined_text)

        rec_char_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )
        splits = rec_char_text_splitter.split_documents(md_header_splits)
        return splits
