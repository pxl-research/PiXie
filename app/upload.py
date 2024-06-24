import gradio as gr
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from blocks_rag_upload import on_file_uploaded, on_file_deleted, list_collections


def on_select(evt: gr.SelectData):  # SelectData is a subclass of EventData
    print(f"You selected {evt.value} at {evt.index} from {evt.target}")
    return gr.Button(interactive=True), evt.value


explainer = (
    "Upload company or business information here if you want the language model to be able to perform lookup into it. "
    "Do not upload data files. "
    "Processing may take considerable time depending on the size of the document. "
    "Do not interrupt the processing step. There is no undo."
)

css = """
.danger {background: red;} 
"""

# https://www.gradio.app/guides/creating-a-custom-chatbot-with-blocks
with gr.Blocks(fill_height=True, title="PiXie", css=css) as llm_client_ui:
    # state that is unique to each user
    selected = gr.State()

    # file uppload UI
    lbl_explainer = gr.HTML(explainer, visible=True)
    file_upload = gr.File(
        label="Click to Upload (a) File(s)",
        file_count="multiple",
        visible=True
    )
    df_files = gr.Dataframe(
        label="Collections",
        headers=["Name"],
        col_count=1,
        interactive=False,
        visible=True,
    )
    btn_delete = gr.Button("Delete", interactive=False, visible=True)

    file_upload.upload(on_file_uploaded, [file_upload], [file_upload, df_files])
    df_files.select(on_select, None, [btn_delete, selected])
    btn_delete.click(on_file_deleted, [df_files, selected], [df_files])

    # global event
    llm_client_ui.load(list_collections, [], [df_files])

# To create a public link, set `share=True` in `launch()`.
llm_client_ui.queue().launch(server_name="0.0.0.0")
