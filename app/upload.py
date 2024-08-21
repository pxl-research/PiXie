import gradio as gr
import logging
from pathlib import Path
from blocks_rag_upload import on_file_uploaded, on_file_deleted
from services.document_manager import list_documents

# Constants
EXPLAINER_TEXT = (
    "Upload company or business information here if you want the language model to be able to perform lookup into it. "
    "Do not upload data files. "
    "Processing may take considerable time depending on the size of the document. "
    "Do not interrupt the processing step. There is no undo."
)

CSS_STYLES = """
.danger {background: red;} 
"""


def on_select(evt: gr.SelectData):  # SelectData is a subclass of EventData
    logging.info(f"User selected {evt.value} at {evt.index} from {evt.target}")
    return gr.Button(interactive=True), evt.value


# Gradio UI
with gr.Blocks(fill_height=True, title="PiXie", css=CSS_STYLES) as llm_client_ui:
    selected = gr.State()  # State that is unique to each user

    # File upload UI
    lbl_explainer = gr.HTML(EXPLAINER_TEXT, visible=True)
    file_upload = gr.File(
        label="Click to Upload (a) File(s)", file_count="multiple", visible=True
    )
    df_files = gr.Dataframe(
        label="Collections",
        headers=["Name"],
        col_count=1,
        interactive=False,
        visible=True,
    )
    btn_delete = gr.Button("Delete", interactive=False, visible=True)

    # Set up the interactions
    file_upload.upload(on_file_uploaded, [file_upload], [file_upload, df_files])
    df_files.select(on_select, None, [btn_delete, selected])
    btn_delete.click(on_file_deleted, [df_files, selected], [df_files])

    # Load event to initialize the document list
    llm_client_ui.load(list_documents, [], [df_files])

# Launch the Gradio app
llm_client_ui.queue().launch(server_name="0.0.0.0", server_port=7861)
