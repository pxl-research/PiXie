import hashlib


def compute_hash(file_path: str) -> str:
    """
    Compute the SHA-256 hash of a file.

    This function reads the file in binary mode and computes its SHA-256 hash.

    Parameters:
        file_path (str): The path to the file to be hashed.

    Returns:
        str: The computed SHA-256 hash of the file.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def read_template(file_path: str) -> str:
    """
    Read and return the content of a template file.

    Parameters:
        file_path (str): The path to the template file.

    Returns:
        str: The content of the template file.
    """
    with open(file_path, "r") as file:
        return file.read()
