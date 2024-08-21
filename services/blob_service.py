import os
import logging
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError


# Environment variables for connection string, storage account name, and container name
CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
STORAGE_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)


def upload_blob(file_path: str, blob_name: str) -> None:
    """
    Upload a file to Azure Blob Storage.

    Parameters:
    - file_path: str : Path to the file to be uploaded.
    - blob_name: str : The name of the blob in Azure Blob Storage.

    Returns:
    - None
    """
    try:
        if not os.path.isfile(file_path):
            logging.error(f"File {file_path} does not exist.")
            raise FileNotFoundError(f"File {file_path} does not exist.")

        blob_client = container_client.get_blob_client(blob_name)
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        logging.info(f"{blob_name} was successfully uploaded.")
    except Exception as e:
        logging.error(f"An error occurred while uploading {blob_name}: {e}")
        raise


def delete_blob(blob_name: str) -> None:
    """
    Delete a blob from Azure Blob Storage.

    Parameters:
    - blob_name: str : The name of the blob to delete.

    Returns:
    - None
    """
    try:
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.delete_blob()
        logging.info(f"{blob_name} was successfully deleted.")
    except ResourceNotFoundError:
        logging.warning(
            f"Blob {blob_name} not found. It may have already been deleted."
        )
    except Exception as e:
        logging.error(f"An error occurred while deleting {blob_name}: {e}")
        raise


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
