import os


def get_mcp_tool_configurations():
    """
    Centraal geconfigureerde MCP tool definities.
    Deze functie retourneert een dictionary met alle tool configuraties.
    """
    return {
        "weather": {
            "command": "python",
            "args": ["src/services/mcp_tools/mcp_weather_tool.py"],
            "transport": "stdio",
        },
        "location": {
            "command": "python",
            "args": ["src/services/mcp_tools/mcp_location_tool.py"],
            "transport": "stdio",
        },
        "rag": {
            "command": "python",
            "args": ["src/services/mcp_tools/mcp_rag_tool.py"],
            "env": {
                "AZURE_BLOB_CONNECTION_STRING": os.getenv(
                    "AZURE_BLOB_CONNECTION_STRING"
                ),
                "AZURE_STORAGE_ACCOUNT_NAME": os.getenv("AZURE_STORAGE_ACCOUNT_NAME"),
                "AZURE_CONTAINER_NAME": os.getenv("AZURE_CONTAINER_NAME"),
                "EMBEDDINGS_MODEL_NAME": os.getenv("EMBEDDINGS_MODEL_NAME"),
                "QDRANT_HOST": os.getenv("QDRANT_HOST"),
                "QDRANT_PORT": os.getenv("QDRANT_PORT"),
            },
        },
        "tabular-rag": {
            "command": "python",
            "args": ["src/services/mcp_tools/mcp_tabular_rag_tool.py"],
            "env": {
                "DEVICE_TYPE": os.getenv("DEVICE_TYPE"),
                "EMBEDDINGS_MODEL_NAME": os.getenv("EMBEDDINGS_MODEL_NAME"),
                "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION"),
                "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
                "AZURE_OPENAI_MODEL_VERSION": os.getenv("AZURE_OPENAI_MODEL_VERSION"),
                "POSTGRES_DB": os.getenv("POSTGRES_DB"),
                "POSTGRES_USER": os.getenv("POSTGRES_USER"),
                "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
                "DEFAULT_LANGUAGE": os.getenv("DEFAULT_LANGUAGE"),
            },
        },
        "tavily-mcp": {
            "command": "npx",
            "args": ["-y", "tavily-mcp@0.1.4"],
            "env": {"TAVILY_API_KEY": os.getenv("TAVILY_API_KEY")},
            "disabled": False,
            "autoApprove": [],
        },
        "github": {
            "command": "docker",
            "args": [
                "run",
                "-i",
                "--rm",
                "-e",
                "GITHUB_PERSONAL_ACCESS_TOKEN",
                "ghcr.io/github/github-mcp-server",
            ],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv(
                    "GITHUB_PERSONAL_ACCESS_TOKEN"
                )
            },
        },
        "sequentialthinking": {
            "command": "docker",
            "args": ["run", "--rm", "-i", "mcp/sequentialthinking"],
        },
    }
