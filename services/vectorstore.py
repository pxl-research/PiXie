import os
import logging
from typing import List
from abc import ABC, abstractmethod
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_community.vectorstores import Qdrant
from langchain_core.embeddings import Embeddings
from services import utils
from langchain.schema import Document


class VectorStore(ABC):
  """
  Abstract base class for a vector store.
  """
  def __init__(self, collection_name: str, embeddings: Embeddings):
    self.collection_name = collection_name
    self.embeddings = embeddings

  @abstractmethod
  def add_document(self, file_path: str):
    """
    Abstract method to add a document to the vector store.
    """
    pass

  @abstractmethod
  def delete_document(self, doc_title: str):
    """
    Abstract method to delete a document from the vector store.
    """
    pass

class QDrantVectorStore(VectorStore):
  """
  QDrant implementation of the VectorStore abstract base class.
  """
  def __init__(self, collection_name: str, embeddings: Embeddings, host: str, port: int):
    super().__init__(collection_name, embeddings)
    self.host = host
    self.port = port

    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    print(qdrant_api_key)
    client = QdrantClient(url=self._get_url(), api_key=qdrant_api_key)
    if not self.check_collection(client, collection_name):
        self.create_collection(client, collection_name)

  def _get_url(self) -> str:
    """
    Returns the URL of the QDrant server.
    """
    return f"{self.host}:{self.port}"

  def add_document(self, chunks: List[Document]):
    """
    Adds a document to the QDrant vector store.
    """
    #Add document to collection
    url = self._get_url()
    Qdrant.from_documents(chunks, self.embeddings, url = url, collection_name=self.collection_name, api_key=os.getenv("QDRANT_API_KEY"))

  def delete_document(self, doc_title):
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(self.host, port=self.port, api_key=qdrant_api_key)
    response = client.delete(
        collection_name=self.collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.doc_title",
                        match=models.MatchValue(value=doc_title)
                    )
                ]
            )
        )
    )
    #self.doc_list = self.doc_list[self.doc_list.doc_title != doc_title]
    #self.doc_list.to_csv(self.doc_list_path, index=False)
    #logging.info(f"Document {doc_title} deleted from the vector store")

  def check_collection(self, client, collection_name):
    """
    Checks if a collection exists in the QDrant vector store.
    """
    response = client.get_collections()
    current_collections = response.collections
    existing_collections = [collection.name for collection in current_collections]
    return collection_name in existing_collections
    
  def create_collection(self, client, collection_name):
    """
    Creates a collection in the QDrant vector store.
    """
    client.create_collection(collection_name = collection_name, 
                             vectors_config=models.VectorParams(size=1024, 
                                                                distance=models.Distance.COSINE))
    logging.info(f"Collection {collection_name} created")

  def retrieve_top_docs(self, question: str, k: int):
      qdrant_api_key = os.getenv("QDRANT_API_KEY")
      client = QdrantClient(self.host, port=self.port, api_key=qdrant_api_key)
      doc_store = Qdrant(client=client, collection_name=self.collection_name, embeddings=self.embeddings)
      result = doc_store.similarity_search(query=question, k=k)
      return result

     
