import logging
import sys

# Configure logging with more detail and better formatting
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG for more detail
    format="%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s",  # Added logger name and line number
    handlers=[
        logging.StreamHandler(sys.stdout),  # Explicitly use stdout
        logging.StreamHandler(sys.stderr),  # Also log to stderr for errors
    ],
    force=True,  # Force reconfiguration if already configured
)

# Set specific loggers to appropriate levels
logging.getLogger("fastmcp").setLevel(logging.DEBUG)
logging.getLogger("mcp_tools").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Reduce HTTP noise
logging.getLogger("requests").setLevel(logging.WARNING)  # Reduce HTTP noise

__version__ = "0.1.0"
__all__ = []
