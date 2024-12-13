from langchain.schema import Document
import pypandoc


class PandocStrategy:
    def process(self, file_path: str) -> list[Document]:
        docs = pypandoc.convert_file(file_path, "md")
        return [Document(page_content=docs)]
