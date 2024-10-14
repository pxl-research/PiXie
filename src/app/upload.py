import logging

import gradio as gr

from blocks_rag_upload import on_file_uploaded, on_file_deleted
from services.document_manager import list_documents

# Constants
EXPLAINER_TEXT = (
    "Upload company or business information here if you want the language model to be able to perform lookup into it. "
    "Do not upload data files. "
    "Processing may take considerable time depending on the size of the document. "
    "Do not interrupt the processing step. There is no undo."
)


def on_select(evt: gr.SelectData):  # SelectData is a subclass of EventData
    logging.info(f"User selected {evt.value} at {evt.index} from {evt.target}")
    return gr.Button(interactive=True), evt.value


def file_upload_interface():
    selected = gr.State()  # State die uniek is voor elke gebruiker

    # Voeg componenten direct toe aan de parent Column (file_upload_section)
    gr.HTML(EXPLAINER_TEXT, visible=True)
    file_upload = gr.File(
        label="Click to Upload (a) File(s)", file_count="multiple", visible=True
    )
    df_files = gr.Dataframe(
        label="Collections",
        headers=["Name"],
        col_count=1,
        interactive=False,
        visible=True,
        value=list_documents(),  # Zorg ervoor dat list_documents een compatibele lijst retourneert
    )
    btn_delete = gr.Button(
        "Delete", interactive=False, visible=True, elem_classes="red_bg"
    )

    # Stel de interacties in
    file_upload.upload(on_file_uploaded, [file_upload], [file_upload, df_files])
    df_files.select(on_select, None, [btn_delete, selected])
    btn_delete.click(on_file_deleted, [df_files, selected], [df_files])
