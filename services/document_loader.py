import os
import pypandoc
import logging
from langchain_community.document_loaders import AzureAIDocumentIntelligenceLoader


class DocumentLoader:

  def load_document(self, file_path: str):
    _, file_name = os.path.split(file_path)
    _, extension = os.path.splitext(file_name)

    print(extension)

    if extension == ".pdf":
      document = self.load_pdf(file_path)
    elif extension == ".docx":
      document = self.load_docx(file_path)
    elif extension == ".md":
      document = self.load_md(file_path)
    else:
      raise Exception("File type not supported")
    return document

  def load_docx(self, file_path: str):
    if not os.path.isfile(file_path):
      logging.error(f"{file_path} does not exist or is not a file.")
      return
    docs = pypandoc.convert_file(file_path, 'md')
    return docs

  def load_md(self, file_path: str):
    if not os.path.isfile(file_path):
      logging.error(f"{file_path} does not exist or is not a file.")
      return
    with open(file_path, 'r') as file:
      docs = file.read()
    return docs

  def load_pdf(self, file_path: str):
    return ''
  

class AzureDocumentLoader(DocumentLoader):

  def load_pdf(self, file_path: str):
    if not os.path.isfile(file_path):
      logging.error(f"{file_path} does not exist or is not a file.")
      return
    
    doc_intelligence_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT_PAID")
    doc_intelligence_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY_PAID")

    self.loader = AzureAIDocumentIntelligenceLoader(
                        file_path = file_path,
                        api_key = doc_intelligence_key, 
                        api_endpoint = doc_intelligence_endpoint,
                        api_version= "2024-02-29-preview",
                        api_model="prebuilt-layout",
                        mode="page")
    docs = self.loader.load()

    return docs