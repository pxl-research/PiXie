import logging
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_qdrant import Qdrant
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from services.abstractclasses.vectorstore import VectorStore


class QDrantVectorStore(VectorStore):
    """
    QDrant implementation of the VectorStore abstract base class.
    """

    def __init__(
        self,
        collection_name: str,
        embeddings: Embeddings,
        client: Optional[QdrantClient] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize the QDrantVectorStore.

        Args:
            collection_name (str): The name of the QDrant collection.
            embeddings (Embeddings): The embeddings model to use.
            client (QdrantClient, optional): An optional QdrantClient instance.
            host (str, optional): The QDrant host.
            port (int, optional): The QDrant port.
        """
        super().__init__(collection_name, embeddings)
        self.client = client or QdrantClient(host=host, port=port)
        self.host = host
        self.port = port

        if not self._check_collection(self.collection_name):
            self._create_collection(self.collection_name)

    def add_document(self, file_name: str, chunks: List[Document]) -> None:
        """
        Adds a document to the QDrant vector store.

        Args:
            file_name (str): The name of the file to add.
            chunks (List[Document]): The document chunks to add.
        """
        for chunk in chunks:
            chunk.metadata["file_name"] = file_name

        try:
            Qdrant.from_documents(
                chunks,
                self.embeddings,
                url=self._get_url(),
                collection_name=self.collection_name,
            )
            logging.info(f"Document {file_name} added to the vector store.")
        except Exception as e:
            logging.error(f"Failed to add document {file_name}: {str(e)}")

    def delete_document(self, doc_title: str) -> None:
        """
        Deletes a document from the QDrant vector store.

        Args:
            doc_title (str): The title of the document to delete.
        """
        try:
            response = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="metadata.doc_title",
                                match=models.MatchValue(value=doc_title),
                            )
                        ]
                    )
                ),
            )
            print(response.status)
            if response.status == "completed":
                logging.info(f"Document {doc_title} deleted from the vector store.")
            else:
                logging.error(
                    f"Failed to delete document {doc_title}. Response: {response}"
                )
        except Exception as e:
            logging.error(f"Failed to delete document {doc_title}: {str(e)}")

    def retrieve_top_chunks(self, question: str, k: int) -> List[Document]:
        """
        Retrieves the top K most similar document chunks to the given question.

        Args:
            question (str): The query to search for.
            k (int): The number of top results to return.

        Returns:
            List[Document]: A list of the top K similar documents.
        """
        try:
            doc_store = Qdrant(
                client=self.client,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )
            result = doc_store.similarity_search(query=question, k=k)
            logging.info(f"Retrieved top {k} chunks for question: {question}")
            return result
        except Exception as e:
            logging.error(f"Failed to retrieve top chunks: {str(e)}")
            return []

    def _check_collection(self, collection_name: str) -> bool:
        """
        Checks if a collection exists in the QDrant vector store.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            bool: True if the collection exists, False otherwise.
        """
        response = self.client.get_collections()
        existing_collections = [collection.name for collection in response.collections]
        return collection_name in existing_collections

    def _create_collection(self, collection_name: str) -> None:
        """
        Creates a collection in the QDrant vector store.

        Args:
            collection_name (str): The name of the collection to create.
        """
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=1024, distance=models.Distance.COSINE
                ),
            )
            logging.info(f"Collection {collection_name} created.")
        except Exception as e:
            logging.error(f"Failed to create collection {collection_name}: {str(e)}")

    def _get_url(self) -> str:
        """
        Returns the URL of the QDrant server.
        """
        return f"http://{self.host}:{self.port}"
