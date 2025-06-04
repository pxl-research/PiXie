from fastmcp import FastMCP
import requests
import os
import json


BASE_URL = "http://10.125.101.11:24031"
ROUTE = "tabular"


mcp = FastMCP(
    name="PiXie Tabular Tool",
    description=(
        "Provides access to structured tabular data most relevant to a given query. Retrieves information from tabular documents to assist in answering questions.",
    ),
)


@mcp.tool()
def tabular_rag_search(question: str, collection_name: str) -> str:
    """
    Retrieves the most relevant structured data from an internal tabular vector store based on a given question.

    This tool connects to a remote search service that finds semantically similar content from stored tabular documents.
    The available content and topics are described in your system prompt - refer to that for guidance on 
    when this tool will be most useful.

    Args:
        question: The search query to find relevant structured information
        collection_name: The collection to search within (use the collection specified in your instructions)

    Returns:
        JSON formatted search results with relevant tabular data and metadata
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
            return f"No tabular data found for collection '{collection_name}'. Please verify the collection name is correct."
        
        if response.status_code != 200:
            return f"Tabular search failed with status {response.status_code}: {response.text}"
            
        data = response.json()
        
        # Check if we got meaningful results
        if not data or (isinstance(data, dict) and not data.get("data")):
            return f"No relevant tabular information found for your question: {question}"
            
        return json.dumps(data, indent=2, default=str)
        
    except requests.exceptions.Timeout:
        return "Tabular search request timed out. Please try again with a more specific question."
    except requests.exceptions.ConnectionError:
        return "Unable to connect to tabular search service. Please try again later."
    except Exception as e:
        return f"Tabular search error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
