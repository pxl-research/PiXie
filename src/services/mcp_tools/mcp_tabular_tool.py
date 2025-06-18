from fastmcp import FastMCP
import requests
import os
import json
from typing import Dict, Any, Optional
from urllib.parse import quote
import logging
import sys

# Ensure MCP tool logging is visible
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add console handler if not already present
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [MCP-TABULAR] %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

logger.info("=== MCP Tabular Tool initializing ===")

BASE_URL = os.getenv("RAG_API_URL")
ROUTE = "tabular"

logger.info(f"BASE_URL from env: {BASE_URL}")
logger.info(f"RAG_API_KEY present: {bool(os.getenv('RAG_API_KEY'))}")


mcp = FastMCP(
    name="PiXie Tabular Tool",
    description=(
        "Provides comprehensive access to structured tabular data with advanced search, schema inspection, and counting capabilities. "
        "Retrieves information from tabular documents to assist in product recommendations and data analysis."
    ),
)


def make_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Helper function to make HTTP requests with consistent error handling"""
    logger.info("Making request to endpoint: %s with params: %s", endpoint, params)
    logger.info(f"{BASE_URL}/{ROUTE}{endpoint}")
    try:
        response = requests.get(
            f"{BASE_URL}/{ROUTE}{endpoint}",
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.getenv("RAG_API_KEY"),
            },
            params=params or {},
            timeout=60,
        )

        if response.status_code == 404:
            # Parse error message to show available tables
            try:
                error_data = response.json()
                if (
                    "detail" in error_data
                    and "Available tables:" in error_data["detail"]
                ):
                    return f"Table not found. {error_data['detail']}"
            except Exception:
                pass
            return f"Resource not found: {endpoint}. Use tabular_list_tables() to see available table names."

        if response.status_code != 200:
            return f"Request failed with status {response.status_code}: {response.text}"

        data = response.json()
        return json.dumps(data, indent=2, default=str)

    except requests.exceptions.Timeout:
        return "Request timed out. Please try again with a more specific query."
    except requests.exceptions.ConnectionError:
        return "Unable to connect to tabular search service. Please try again later."
    except Exception as e:
        return f"Request error: {str(e)}"


@mcp.tool()
def tabular_rag_search(
    question: str,
    collection_name: str,
    top_k: int = 30,
    k_rrf: int = 60,
    max_file_count: int = 3,
    try_iteration_max_count: int = 3,
    is_recommendation_system: bool = False,
) -> str:
    """
    Search for relevant structured data from tabular documents based on a question.

    This is the main search function that finds semantically similar content from stored tabular documents.
    Use this to find products, specifications, prices, and other structured information.

    Args:
        question: The search query to find relevant structured information
        collection_name: The collection to search within (use the collection specified in your instructions)
        top_k: Number of top results to return (default: 30)
        k_rrf: RRF (Reciprocal Rank Fusion) parameter for ranking (default: 60)
        max_file_count: Maximum number of files to consider (default: 3)
        try_iteration_max_count: Maximum number of retry attempts (default: 3)
        is_recommendation_system: Enable recommendation system mode (default: False)

    Returns:
        JSON formatted search results with relevant tabular data and metadata
    """
    params = {
        "question": question,
        "top_k": top_k,
        "k_rrf": k_rrf,
        "max_file_count": max_file_count,
        "try_iteration_max_count": try_iteration_max_count,
        "is_recommendation_system": True,  # is_recommendation_system,
    }

    return make_request(f"/collections/{collection_name}/search", params)


@mcp.tool()
def tabular_list_tables(collection_name: str) -> str:
    """
    List all tables/files available in a collection.
    This shows the exact table names you must use in other function calls.
    """
    logger.info(f"tabular_list_tables called with collection_name: {collection_name}")
    logger.info(f"BASE_URL: {BASE_URL}")
    logger.info(f"RAG_API_KEY present: {bool(os.getenv('RAG_API_KEY'))}")

    if collection_name in ["products", "inventory", "database"]:
        return f"ERROR: '{collection_name}' is not a valid collection name. Use the collection name provided in your system prompt."

    result = make_request(f"/collections/{collection_name}/tables")
    logger.info(f"Result: {result[:200]}...")  # Log first 200 chars

    # Add helper information
    try:
        data = json.loads(result)
        if "items" in data:
            tables = data["items"]
            helper_info = {
                "available_tables": tables,
                "usage_note": "Use these EXACT table names in other function calls. For Excel files with sheets, use 'filename.xlsx#sheetname' format.",
                "url_encoding_note": "The MCP tool handles URL encoding automatically - just use the exact names shown above.",
            }
            return json.dumps(helper_info, indent=2)
    except Exception:
        pass

    return result


@mcp.tool()
def tabular_get_table_schema(collection_name: str, file_name: str) -> str:
    """
    Get the complete schema for a specific table.

    Args:
        collection_name: The collection containing the table
        file_name: Use the EXACT table name from tabular_list_tables()
                   For Excel sheets: 'filename.xlsx#sheetname'
    """
    if collection_name in ["products", "inventory", "database"]:
        return f"ERROR: '{collection_name}' is not a valid collection name."
    # URL encode the file name properly
    encoded_file_name = quote(file_name, safe="")

    return make_request(
        f"/collections/{collection_name}/tables/{encoded_file_name}/columns"
    )


@mcp.tool()
def tabular_get_column_names(collection_name: str, file_name: str) -> str:
    """
    Get just the column names for a specific table.

    Use this for a quick overview of available columns without the full schema details.
    Useful when you need to know what fields are available for searching.

    Args:
        collection_name: The collection containing the table
        file_name: The name of the table/file to get columns from

    Returns:
        JSON with list of column names
    """
    return make_request(
        f"/collections/{collection_name}/tables/{file_name}/columns/names"
    )


@mcp.tool()
def tabular_count_matching_rows(
    collection_name: str,
    file_name: str,
    question: str,
    k_rrf: int = 60,
    try_iteration_max_count: int = 3,
    is_recommendation_system: bool = False,
) -> str:
    """
    Count matching rows for a search query.

    Args:
        collection_name: The collection name
        file_name: Use EXACT table name from tabular_list_tables()
        question: Search query
    """
    if collection_name in ["products", "inventory", "database"]:
        return f"ERROR: '{collection_name}' is not a valid collection name."
    # URL encode the file name properly
    encoded_file_name = quote(file_name, safe="")

    params = {
        "question": question,
        "k_rrf": k_rrf,
        "try_iteration_max_count": try_iteration_max_count,
        "is_recommendation_system": is_recommendation_system,
    }

    return make_request(
        f"/collections/{collection_name}/tables/{encoded_file_name}/count", params
    )


@mcp.tool()
def tabular_search_with_count(
    question: str, collection_name: str, max_results: int = 10
) -> str:
    """
    Advanced search that first counts results, then retrieves appropriate number of rows.

    This is a convenience function that combines counting and searching for better
    control over result sizes. Use this when you want to avoid getting too many
    or too few results.

    Args:
        question: The search query
        collection_name: The collection to search in
        max_results: Maximum number of results to return (default: 10)

    Returns:
        JSON with search results and metadata about total matches
    """
    # First, do a basic search to get some results and understand the data structure
    search_result = tabular_rag_search(
        question=question, collection_name=collection_name, top_k=max_results
    )

    try:
        # Parse the result to add count information
        result_data = json.loads(search_result)
        if isinstance(result_data, dict) and "data" in result_data:
            result_data["requested_max"] = max_results
            result_data["actual_returned"] = len(result_data["data"])
            return json.dumps(result_data, indent=2, default=str)
        else:
            return search_result
    except Exception:
        return search_result


if __name__ == "__main__":
    mcp.run(transport="stdio")
