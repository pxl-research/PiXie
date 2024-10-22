import logging
import pandas as pd
import gradio as gr

from services.document_manager import list_documents, remove_document, add_documents

# Constants
EXPLAINER_TEXT = (
    "Upload company or business information here if you want the language model to be able to perform lookup into it. "
    "Do not upload data files. "
    "Processing may take considerable time depending on the size of the document. "
    "Do not interrupt the processing step. There is no undo."
)


def on_select_file(evt: gr.SelectData):
    """
    Handles the file selection event from the DataFrame.

    This function is triggered when a user selects a row in the `files_list` DataFrame.
    It retrieves the selected filename and logs the selection event. It also updates
    the 'Delete' button to be interactive, allowing the user to delete the selected file.

    Parameters:
        evt (gr.SelectData): The selection event data containing information about the selected row.

    Returns:
        tuple:
            - gr.update(interactive=True): An update instruction to make the 'Delete' button interactive.
            - str: The name of the selected file.
    """
    if isinstance(evt.value, list):
        selected_filename = evt.value[0]
    else:
        selected_filename = evt.value
    logging.info(f"User selected {selected_filename} at {evt.index} from {evt.target}")
    return gr.update(interactive=True), selected_filename


def load_files_list():
    """
    Loads and returns the updated list of available files.

    This internal function retrieves the current list of documents and converts it into a Pandas DataFrame.

    Returns:
        pd.DataFrame: A DataFrame containing the names of the files under the column "Naam".
    """
    df = list_documents()
    return df


def file_upload_interface():
    """
    Creates and returns the Gradio interface for file management, including uploading and deleting files.

    This function initializes the components of the interface, such as the file upload button, the DataFrame
    displaying the list of files, the delete button, and a feedback section. It also defines the interactions
    between these components, such as selecting a file and deleting it.

    Returns:
        tuple:
            - gr.Dataframe: The DataFrame component that displays the list of files.
            - gr.File: The file upload component allowing users to upload multiple files.
            - gr.Button: The delete button used to remove the selected file.
            - gr.Markdown: The Markdown component for displaying feedback to the user.
            - function: A function to load and refresh the list of files.
    """
    selected_file = gr.State()
    gr.HTML(EXPLAINER_TEXT, visible=True)

    file_upload = gr.File(
        label="Click to Upload (a) File(s)", file_count="multiple", visible=True
    )

    feedback = gr.Markdown("")

    files_list = gr.Dataframe(
        headers=["Naam"],
        datatype=["str"],
        value=list_documents(),
        interactive=False,
    )

    delete_file_button = gr.Button("Delete", interactive=False, elem_classes="red_bg")

    # Define interactions
    files_list.select(
        fn=on_select_file, inputs=None, outputs=[delete_file_button, selected_file]
    )

    delete_file_button.click(
        remove_document,
        [selected_file],
        [feedback, files_list],
        queue=False,
    )

    file_upload.upload(add_documents, [file_upload], [files_list])

    return (files_list, file_upload, delete_file_button, feedback, load_files_list)
