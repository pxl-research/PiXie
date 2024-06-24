import gradio as gr
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from blocks_llm_chat_with_rag import append_user, append_ai, clear_log

css = """
.danger {background: red;} 
"""

# https://www.gradio.app/guides/creating-a-custom-chatbot-with-blocks
with gr.Blocks(fill_height=True, title="PiXie", css=css) as llm_client_ui:

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

        # event handlers
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

# To create a public link, set `share=True` in `launch()`.
llm_client_ui.queue().launch(server_name="0.0.0.0")
