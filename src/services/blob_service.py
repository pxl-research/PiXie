import os
import logging


logger = logging.getLogger(__name__)

# Environment variables for connection string, storage account name, and container name
STORAGE_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

# Log configuration validation
if not STORAGE_NAME:
    logger.warning("AZURE_STORAGE_ACCOUNT_NAME environment variable not set")
if not CONTAINER_NAME:
    logger.warning("AZURE_CONTAINER_NAME environment variable not set")

logger.debug(
    f"Blob service initialized - storage_name: {STORAGE_NAME}, container_name: {CONTAINER_NAME}"
)


def generate_blob_url(blob_name: str) -> str:
    """
    Generate a URL for a blob in Azure Blob Storage.

    Parameters:
    - blob_name: str : The name of the blob.

    Returns:
    - str : The URL of the blob.
    """
    try:
        if not blob_name:
            logger.error("Error generating blob URL - blob_name is empty or None")
            raise ValueError("blob_name cannot be empty or None")

        if not STORAGE_NAME or not CONTAINER_NAME:
            logger.error(
                "Error generating blob URL - missing required environment variables"
            )
            raise ValueError(
                "AZURE_STORAGE_ACCOUNT_NAME and AZURE_CONTAINER_NAME must be set"
            )

        logger.debug(f"Generating blob URL - blob_name: {blob_name}")

        url = (
            f"https://{STORAGE_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
        )

        logger.info(
            f"Blob URL generated successfully - blob_name: {blob_name}, url_length: {len(url)}"
        )
        return url

    except Exception as e:
        logger.error(
            f"Error generating blob URL - blob_name: {blob_name if 'blob_name' in locals() else 'unknown'}: {e}",
            exc_info=True,
        )
        raise
