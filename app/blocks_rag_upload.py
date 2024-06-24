import gradio as gr
import os
from services import utils
import shutil
from werkzeug.utils import secure_filename
from app import document_loader, splitter, vector_store

UPLOAD_FOLDER = "./uploads"
DOC_LIST_PATH = "../assets/helper/doc_list.csv"


def list_collections():
    doc_list = utils.get_doc_list(DOC_LIST_PATH)
    names = []
    for file_name in doc_list["file_name"]:
        names.append([file_name])
    return names


def on_file_uploaded(file_paths: list[str], progress=gr.Progress()):
    # 1. Check if file is already uploaded and/or should be replaced with a newer version
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)

    for file_path in file_paths:
        shutil.copy(file_path, UPLOAD_FOLDER)

        file_name = os.path.basename(file_path)
        secure_file_name = secure_filename(file_name)

        file_hash = utils.compute_hash(file_path)

        if utils.is_doc_up_to_date_in_list(file_hash, DOC_LIST_PATH):
            # TODO: Update the last updated date in the doc_list.csv
            return [None, []]

        delete = utils.is_doc_in_list(secure_file_name, DOC_LIST_PATH)

        # 2. Load the document
        document = document_loader.load_document(file_path)

        # 3. Split the document
        chunks = splitter.split(document)

        # 4. Add the document to the vector store
        vector_store.add_document(secure_file_name, chunks)

        # 5. Add file to the list
        utils.add_to_doc_list(DOC_LIST_PATH, secure_file_name, file_hash, delete)
        names = list_collections()
    return [file_paths, names]


def on_file_deleted(df_files: gr.Dataframe, selected: gr.State):
    # 1. Remove the document from the vector store
    vector_store.delete_document(selected)
    # 2. Remove the document from the doc_list.csv
    utils.remove_from_doc_list(DOC_LIST_PATH, selected)
    # 3. Remove the document from the dataframe
    df_files = df_files[df_files.iloc[:, 0] != selected]
    print(f"Removing document {selected} from the vector store and doc_list.csv.")
    return df_files
