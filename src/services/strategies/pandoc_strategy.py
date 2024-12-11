from langchain.schema import Document
from typing import List
import pypandoc


class PandocStrategy:
    def process(self, file_path: str) -> List[Document]:
        docs = pypandoc.convert_file(file_path, "md")
        return [Document(page_content=docs)]
