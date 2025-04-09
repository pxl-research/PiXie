from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server with configuration
mcp = FastMCP(
    "Location",  # Name of the MCP server
    instructions="You are a location assistant that knows the current location of the user.",
)


@mcp.tool()
async def get_current_location() -> str:
    """
    Get current location of the user.

    This function returns the current location of the user.

    Args:
        None

    Returns:
        str: A string containing the current location of the user
    """
    return "The current location of the user is Hasselt."


if __name__ == "__main__":
    # Start the MCP server with stdio transport
    # stdio transport allows the server to communicate with clients
    # through standard input/output streams, making it suitable for
    # local development and testing
    mcp.run(transport="stdio")
