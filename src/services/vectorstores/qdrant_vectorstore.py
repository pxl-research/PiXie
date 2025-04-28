import logging
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_qdrant import QdrantVectorStore as QVStore
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from services.abstractclasses.vectorstore import VectorStore


class QDrantVectorStore(VectorStore):
    """
    QDrant implementation of the VectorStore abstract base class.
    """

    def __init__(
        self,
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
        super().__init__(embeddings)
        self.client = client or QdrantClient(host=host, port=port)
        self.host = host
        self.port = port

        current_collections = self.list_collections()
        if not current_collections:
            default_collection_name = "pixie"
            self._create_collection(default_collection_name)

    def add_document(
        self, collection_name: str, file_name: str, chunks: List[Document]
    ) -> None:
        """
        Adds a document to the QDrant vector store.

        Args:
            file_name (str): The name of the file to add.
            chunks (List[Document]): The document chunks to add.
        """
        for chunk in chunks:
            chunk.metadata["file_name"] = file_name

        try:
            QVStore.from_documents(
                chunks,
                self.embeddings,
                url=self._get_url(),
                collection_name=collection_name,
            )
            logging.info(f"Document {file_name} added to {collection_name}.")
        except Exception as e:
            logging.error(f"Failed to add document {file_name}: {str(e)}")

    def delete_document(self, collection_name: str, file_name: str) -> None:
        """
        Deletes a document from the QDrant vector store.

        Args:
            doc_title (str): The title of the document to delete.
        """
        try:
            response = self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="metadata.doc_title",
                                match=models.MatchValue(value=file_name),
                            )
                        ]
                    )
                ),
            )
            if response.status == "completed":
                logging.info(f"Document {file_name} deleted from {collection_name}.")
            else:
                logging.error(
                    f"Failed to delete document {file_name}. Response: {response}"
                )
        except Exception as e:
            logging.error(f"Failed to delete document {file_name}: {str(e)}")

    def retrieve_top_chunks(
        self, collection_name: str, question: str, k: int
    ) -> List[Document]:
        """
        Retrieves the top K most similar document chunks to the given question.

        Args:
            question (str): The query to search for.
            k (int): The number of top results to return.

        Returns:
            List[Document]: A list of the top K similar documents.
        """
        try:
            doc_store = QVStore(
                client=self.client,
                collection_name=collection_name,
                embedding=self.embeddings,
            )
            result = doc_store.similarity_search(query=question, k=k)
            logging.info(f"Retrieved top {k} chunks for question: {question}")
            return result
        except Exception as e:
            logging.error(f"Failed to retrieve top chunks: {str(e)}")
            return []

    def fast_retrieve_top_chunks(
        self, collection_name: str, question: str, k: int
    ) -> List[Document]:
        """
        Retrieves the top K most similar document chunks quickly using direct Qdrant API calls.

        Args:
            collection_name (str): Name of the collection.
            question (str): The query to search for.
            k (int): The number of top results to return.

        Returns:
            List[Document]: A list of the top K similar documents.
        """
        try:
            # 1. Embed the query
            embedded_query = self.embeddings.embed_query(question)

            # 2. Use direct Qdrant client search
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=embedded_query,
                limit=k,
                with_payload=True,
            )

            # 3. Convert the search results to Document instances
            documents = []
            for point in search_result:
                content = point.payload.get("page_content", "")
                metadata = point.payload.get("metadata", {})
                documents.append(Document(page_content=content, metadata=metadata))

            logging.info(
                f"Retrieved {len(documents)} documents (fast mode) for question: {question}"
            )
            return documents

        except Exception as e:
            logging.error(f"Fast retrieval failed: {str(e)}")
            return []

    def list_collections(self) -> List[str]:
        """
        Lists all collections in the QDrant vector store.

        Returns:
            List[str]: A list of collection names.
        """
        response = self.client.get_collections()
        existing_collections = [collection.name for collection in response.collections]
        return existing_collections

    def add_collection(self, collection_name: str) -> None:
        """
        Adds a collection to the QDrant vector store.

        Args:
            collection_name (str): The name of the collection to add.
        """

        if not self._check_collection(collection_name):
            self._create_collection(collection_name)
        else:
            logging.info(f"Collection {collection_name} already exists.")

    def _check_collection(self, collection_name: str) -> bool:
        """
        Checks if a collection exists in the QDrant vector store.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            bool: True if the collection exists, False otherwise.
        """
        existing_collections = self.list_collections()
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
