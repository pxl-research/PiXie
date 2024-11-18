from docling.document_converter import DocumentConverter
from services.abstractclasses.document_loader import DocumentLoader


class DoclingDocumentLoader(DocumentLoader):

    def __init__(self):
        super().__init__()
        self.loader_name = "Docling"

    def load_pdf(self, file_path):

        self.loader = DocumentConverter()
        result = self.loader.convert(file_path)
        return result.document.export_to_markdown()

    def load_pptx(self, file_path):

        self.loader = DocumentConverter()
        result = self.loader.convert(file_path)
        return result.document.export_to_markdown()
