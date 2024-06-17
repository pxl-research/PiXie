import gradio as gr
import os
from services import utils
import shutil
from werkzeug.utils import secure_filename
from app import document_loader

UPLOAD_FOLDER = './uploads'
DOC_LIST_PATH = 'doc_list.csv'

def list_collections():
    doc_list = utils.get_doc_list(DOC_LIST_PATH)
    names = []
    for file_name in doc_list['file_name']:
        names.append([file_name])
    return names

def on_file_uploaded(file_path: str, progress=gr.Progress()):
    # 1. Check if file is already uploaded and/or should be replaced with a newer version
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    shutil.copy(file_path, UPLOAD_FOLDER)

    file_name = os.path.basename(file_path)
    secure_file_name = secure_filename(file_name)

    file_hash = utils.compute_hash(file_path)

    if utils.is_doc_up_to_date_in_list(file_hash, DOC_LIST_PATH):
        #TODO: Update the last updated date in the doc_list.csv
        return [None, []]
    
    delete = utils.is_doc_in_list(secure_file_name, DOC_LIST_PATH)

    # 2. Load the document
    document = document_loader.load_document(file_path)

    #3. Split the document

    #3. Add file to the list
    utils.add_to_doc_list(DOC_LIST_PATH, secure_file_name, file_hash, delete)
    names = list_collections()
    return [file_path, names]