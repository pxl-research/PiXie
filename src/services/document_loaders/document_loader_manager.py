import os
from enum import Enum
from dotenv import load_dotenv


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
