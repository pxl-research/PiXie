import hashlib
from pandas import read_csv, DataFrame, concat, Timestamp

def compute_hash(file_path):
    sha256_hash = hashlib.sha256()

    with open(file_path,"rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()

def is_doc_up_to_date_in_list(file_hash, doc_list_path):
    doc_list = read_csv(doc_list_path)
    if doc_list.empty:
        return False
    return file_hash in doc_list['file_hash'].values

def is_doc_in_list(file_name, doc_list_path):
    doc_list = read_csv(doc_list_path)
    if doc_list.empty:
        return False
    return file_name in doc_list['file_name'].values

def read_template(file_path):
    with open(file_path, 'r') as file:
        template = file.read()
    return template

def add_to_doc_list(doc_list_path: str, file_name: str, file_hash: str, delete: bool = False):
    """
    Adds a document to the document list.
    """
    doc_list = read_csv(doc_list_path)
    new_row = DataFrame({"file_name": [file_name], "file_hash": [file_hash], "last_updated": [Timestamp.now()]})
    doc_list = concat([doc_list, new_row], ignore_index=True)
    doc_list.to_csv(doc_list_path, index=False)

def get_doc_list(doc_list_path: str):
    """
    Returns the document list.
    """
    return read_csv(doc_list_path)
