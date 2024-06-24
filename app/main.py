import gradio as gr
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from blocks_llm_chat_with_rag import append_user, append_ai, clear_log
from blocks_rag_upload import on_file_uploaded, on_file_deleted, list_collections


def show_live():
    return {
        cb_live: gr.Chatbot(visible=True),
        gr_live: gr.Group(visible=True),
        row_live: gr.Row(visible=True),
        btn_live: gr.Button(interactive=False),
        lbl_explainer: gr.HTML(visible=False),
        file_upload: gr.File(visible=False),
        df_files: gr.Dataframe(visible=False),
        btn_delete: gr.Button(visible=False),
        btn_upload: gr.Button(interactive=True),
    }

def show_upload():
    return {
        cb_live: gr.Chatbot(visible=False),
        gr_live: gr.Group(visible=False),
        row_live: gr.Row(visible=False),
        btn_live: gr.Button(interactive=True),
        lbl_explainer: gr.HTML(visible=True),
        file_upload: gr.File(visible=True),
        df_files: gr.Dataframe(visible=True),
        btn_delete: gr.Button(visible=True),
        btn_upload: gr.Button(interactive=False),
    }


def on_select(evt: gr.SelectData):  # SelectData is a subclass of EventData
    print(f"You selected {evt.value} at {evt.index} from {evt.target}")
    return gr.Button(interactive=True), evt.value


explainer = (
    "Upload company or business information here if you want the language model to be able to perform lookup into it. "
    "Do not upload data files. Stick to PDF only. "
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

    # live client UI
    cb_live = gr.Chatbot(label="Chat", scale=1)
    with gr.Group() as gr_live:
        with gr.Row():
            tb_user = gr.Textbox(
                show_label=False, placeholder="Enter prompt here...", scale=10
            )
            btn_send = gr.Button(
                "", scale=0, min_width=64, icon="../assets/icons/send.png"
            )
            btn_remove = gr.Button(
                "", scale=0, min_width=64, icon="../assets/icons/disposal.png"
            )
    with gr.Row() as row_live:
        lbl_debug = gr.HTML("")

        # event handlers
        tb_user.submit(append_user, [tb_user, cb_live], [cb_live]).then(
            append_ai,
            [tb_user, cb_live],
            [tb_user, cb_live, lbl_debug],
        )
        btn_send.click(append_user, [tb_user, cb_live], [cb_live]).then(
            append_ai,
            [tb_user, cb_live],
            [tb_user, cb_live, lbl_debug],
        )
        btn_remove.click(clear_log, None, [tb_user, cb_live])

    # file uppload UI
    lbl_explainer = gr.HTML(explainer, visible=False)
    file_upload = gr.File(
        label="Click to Upload a File",
        file_types=[".pdf"],
        file_count="single",
        visible=False,
    )
    df_files = gr.Dataframe(
        label="Collections",
        headers=["Name"],
        col_count=1,
        interactive=False,
        visible=False,
        scale=1,
    )
    btn_delete = gr.Button("Delete", interactive=False, visible=False)

    file_upload.upload(on_file_uploaded, [file_upload], [file_upload, df_files])
    df_files.select(on_select, None, [btn_delete, selected])
    btn_delete.click(on_file_deleted, [df_files, selected], [df_files])

    # toggle UI
    with gr.Row():
        btn_live = gr.Button("Chat", icon="../assets/icons/chat.png", interactive=False)
        btn_upload = gr.Button("Upload")

        # event handlers
        btn_live.click(
            show_live,
            [],
            [
                cb_live,
                gr_live,
                row_live,
                file_upload,
                df_files,
                lbl_explainer,
                btn_live,
                btn_delete,
                btn_upload,
            ],
        )
        btn_upload.click(
            show_upload,
            [],
            [
                cb_live,
                gr_live,
                row_live,
                file_upload,
                df_files,
                lbl_explainer,
                btn_live,
                btn_delete,
                btn_upload,
            ],
        )
    # global event
    llm_client_ui.load(list_collections, [], [df_files])

# To create a public link, set `share=True` in `launch()`.
llm_client_ui.queue().launch(server_name="0.0.0.0")