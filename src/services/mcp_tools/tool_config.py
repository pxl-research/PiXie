import os
from langchain_core.tools import tool


@tool
def ask_user(prompt: str) -> str:
    """
    Vraag extra input van de gebruiker op via de interface.
    Gebruik dit wanneer je een verduidelijking nodig hebt.

    Args:
        prompt: De vraag die je aan de gebruiker wil stellen.
    Returns:
        De input die de gebruiker gaf.
    """
    return f"__user_input_required__::{prompt}"


def load_env_vars(*keys):
    """
    Load the specified environment variables.

    Parameters:
        *keys: Names of the environment variables to load.

    Returns:
        dict: A mapping of each key to its environment variable value.
    """
    return {key: os.getenv(key) for key in keys}


def get_mcp_tool_configurations():
    """
    Return a dictionary of configurations for all MCP tools.

    Returns:
        dict: A mapping of tool names to their configuration settings,
              including command, args, env, disabled, and autoApprove if applicable.
    """
    return {
        "tavily-mcp": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "tavily-mcp@0.1.4"],
            "env": load_env_vars("TAVILY_API_KEY"),
            "disabled": False,
            "autoApprove": [],
        },
        "sequentialthinking": {
            "transport": "stdio",
            "command": "docker",
            "args": ["run", "--rm", "-i", "mcp/sequentialthinking"],
        },
        "rag": {
            "transport": "stdio",
            "command": "python",
            "args": ["src/services/mcp_tools/mcp_rag_tool.py"],
            "env": {**load_env_vars("RAG_API_KEY")},
        },
        "tabular": {
            "transport": "stdio",
            "command": "python",
            "args": ["src/services/mcp_tools/mcp_tabular_tool.py"],
            "env": {**load_env_vars("RAG_API_KEY")},
        },
    }
