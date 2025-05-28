import os
import logging


# Environment variables for connection string, storage account name, and container name
STORAGE_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")


def generate_blob_url(blob_name: str) -> str:
    """
    Generate a URL for a blob in Azure Blob Storage.

    Parameters:
    - blob_name: str : The name of the blob.

    Returns:
    - str : The URL of the blob.
    """
    url = f"https://{STORAGE_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}"
    logging.info(f"Generated URL for blob {blob_name}: {url}")
    return url
