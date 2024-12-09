from langchain.schema import Document
from docling.document_converter import DocumentConverter
from typing import List


class DoclingStrategy:
    def process(self, file_path: str) -> List[Document]:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        content = result.document.export_to_markdown()
        return [Document(page_content=content)]
