from langchain.schema import Document
from docling.document_converter import DocumentConverter


class DoclingStrategy:
    def process(self, file_path: str) -> list[Document]:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        content = result.document.export_to_markdown()
        return [Document(page_content=content)]
