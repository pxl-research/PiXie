from fastmcp import FastMCP
import requests
import os
import json


BASE_URL = "http://10.125.101.11:24031"
ROUTE = "tabular"


mcp = FastMCP(
    name="PiXie Tabular Tool",
    description=(
        "Provides access to internal document segments most relevant to a given query. Useful for retrieving contextual information to assist in answering user questions.",
    ),
)


@mcp.tool()
def search(question: str, collection_name: str) -> str:
    """
    This MCP tool allows the LLM to retrieve the most relevant document chunks from an internal vector store,
    based on a given question. The tool is typically used after the LLM has reviewed available document summaries
    and wants to search for detailed content.

    It connects to a remote FastAPI server that exposes a `/search` endpoint. The response includes the top-matching
    chunks ranked by semantic similarity, intended to support evidence-based answering within internal document contexts.

    Use this tool when the summaries alone are insufficient to answer the user's question.
    """

    response = requests.get(
        f"{BASE_URL}/{ROUTE}/search",
        headers={
            "Content-Type": "application/json",
            "x-api-key": os.getenv("RAG_API_KEY"),
        },
        params={
            "question": question,
            "collection_name": "pixie",
        },
        timeout=10,
    )
    if response.status_code != 200:
        return f"Something went wrong: {response.status_code} - {response.text}"
    data = response.json()
    return json.dumps(data, indent=2, default=str)


if __name__ == "__main__":
    mcp.run(transport="stdio")
