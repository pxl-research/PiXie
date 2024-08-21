import gradio as gr
import os
import shutil
from werkzeug.utils import secure_filename
from services.document_manager import add_document, remove_document, list_documents


def on_file_uploaded(file_paths: list[str], progress=gr.Progress()) -> list:
    """
    Handle the event when files are uploaded via the Gradio interface.

    Parameters:
    - file_paths: list[str]
        The list of file paths that were uploaded.
    - progress: gr.Progress
        A progress indicator for the Gradio UI.

    Returns:
    - list: Updated file paths and collection names.
    """
    for file_path in file_paths:
        add_document(file_path)

    # Get the updated list of document collections
    names = list_documents()

    # Return the original file paths and the updated document list
    return [file_paths, names]


def on_file_deleted(df_files: gr.Dataframe, selected: str) -> gr.Dataframe:
    """
    Handle the event when a file is deleted via the Gradio interface.

    Parameters:
    - df_files: gr.Dataframe
        The dataframe of files currently listed.
    - selected: str
        The name of the selected file to delete.

    Returns:
    - gr.Dataframe: The updated dataframe after the file has been removed.
    """
    # Remove the document using the document manager
    remove_document(selected)

    # Update the dataframe by removing the selected file
    df_files = df_files[df_files.iloc[:, 0] != selected]

    return df_files
