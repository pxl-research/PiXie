from fastmcp import FastMCP
import requests
import os
import json


BASE_URL = "http://10.125.101.11:24031"
ROUTE = "rag"


mcp = FastMCP(
    name="PiXie RAG Tool",
    description=(
        "Provides access to internal document segments most relevant to a given query. Retrieves contextual information from stored documents to assist in answering questions.",
    ),
)


@mcp.tool()
def rag_search(question: str, collection_name: str) -> str:
    """
    Retrieves the most relevant document chunks from an internal vector store based on a given question.

    This tool connects to a remote search service that finds semantically similar content from stored documents.
    The available content and topics are described in your system prompt - refer to that for guidance on 
    when this tool will be most useful.

    Args:
        question: The search query to find relevant information
        collection_name: The collection to search within (use the collection specified in your instructions)

    Returns:
        JSON formatted search results with relevant document chunks and metadata
    """

    try:
        response = requests.get(
            f"{BASE_URL}/{ROUTE}/collections/{collection_name}/search",
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.getenv("RAG_API_KEY"),
            },
            params={
                "question": question,
            },
            timeout=15,
        )
        
        if response.status_code == 404:
            return f"No information found for collection '{collection_name}'. Please verify the collection name is correct."
        
        if response.status_code != 200:
            return f"Search failed with status {response.status_code}: {response.text}"
            
        data = response.json()
        
        # Check if we got meaningful results
        if not data or (isinstance(data, dict) and not data.get("chunks")):
            return f"No relevant information found for your question: {question}"
            
        return json.dumps(data, indent=2, default=str)
        
    except requests.exceptions.Timeout:
        return "Search request timed out. Please try again with a more specific question."
    except requests.exceptions.ConnectionError:
        return "Unable to connect to search service. Please try again later."
    except Exception as e:
        return f"Search error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
