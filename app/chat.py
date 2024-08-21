import os

import gradio as gr

from blocks_llm_chat_with_rag import append_user, append_ai, clear_log

# Constants
CSS_STYLES = """
.danger {background: red;} 
"""
SEND_ICON_PATH = os.path.join("..", "assets", "icons", "send.png")
DISPOSAL_ICON_PATH = os.path.join("..", "assets", "icons", "disposal.png")

# Gradio UI Setup
with gr.Blocks(fill_height=True, title="PiXie", css=CSS_STYLES) as llm_client_ui:
    gr.Markdown("# <center>Vraag het aan PiXie</center>")
    cb_live = gr.Chatbot(label="Geschiedenis", scale=1)
    with gr.Group() as gr_live:
        with gr.Row():
            tb_user = gr.Textbox(
                show_label=False, placeholder="Stel hier je vraag...", scale=10
            )
            btn_send = gr.Button(
                "", scale=0, min_width=64, icon=SEND_ICON_PATH
            )
            btn_remove = gr.Button(
                "", scale=0, min_width=64, icon=DISPOSAL_ICON_PATH
            )

        # Event handlers
        tb_user.submit(append_user, [tb_user, cb_live], [cb_live]).then(
            append_ai,
            [tb_user, cb_live],
            [tb_user, cb_live],
        )
        btn_send.click(append_user, [tb_user, cb_live], [cb_live]).then(
            append_ai,
            [tb_user, cb_live],
            [tb_user, cb_live],
        )
        btn_remove.click(clear_log, None, [tb_user, cb_live])

# Launch the Gradio app
llm_client_ui.queue().launch(server_name="0.0.0.0", server_port=7868)
