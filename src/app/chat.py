import os

import gradio as gr

from blocks_llm_chat_with_rag import (
    append_user,
    append_ai,
    clear_log,
)

from services.authentication.authentication_manager import custom_auth
from services.chat_history.chat_history_manager import get_chat_history
from typing import List, Tuple, Optional, Dict, Any
from langchain_core.messages import AIMessage, HumanMessage


# Constants
CSS_STYLES = """
    .red_bg {background: red}
    .green_bg {background: green}
    footer {display:none !important}
"""
SEND_ICON_PATH = os.path.join("src", "assets", "icons", "send.png")
DISPOSAL_ICON_PATH = os.path.join("src", "assets", "icons", "disposal.png")


def load_chat_history(user_info):
    if user_info and "id" in user_info:
        user_id = user_info["id"]
        chat_history = get_chat_history(user_id, limit=10)
        return chat_history
    return []


def login(username: str, password: str, user_state: Optional[Dict[str, Any]] = None):
    """
    Authenticeer de gebruiker en sla de gebruikersinformatie op in de state.

    Parameters:
        username (str): De gebruikersnaam van de gebruiker.
        password (str): Het wachtwoord van de gebruiker.
        user_state (dict, optional): De huidige gebruikersstate.

    Returns:
        Tuple[gr.update, str, Dict[str, Any]]:
            - Update object om de login velden te verbergen.
            - Feedback bericht.
            - Gebruikersinformatie opgeslagen in de state.
    """
    user = custom_auth(username, password)
    if user:
        chatbot = load_chat_history(user)
        return gr.update(visible=False), gr.update(visible=True), chatbot, user
    else:
        return gr.update(visible=True), gr.update(visible=False), None


# Gradio UI Setup
with gr.Blocks(fill_height=True, title="PiXie", css=CSS_STYLES) as llm_client_ui:
    user_info = gr.State(value=None)
    chat_history_state = gr.State(value=[])

    gr.Markdown("# <center>Vraag het aan PiXie</center>")
    with gr.Column(visible=True) as login_row:
        with gr.Row(visible=True):

            username = gr.Textbox(label="Username", placeholder="Enter your username")
            password = gr.Textbox(
                label="Password", placeholder="Enter your password", type="password"
            )
        login_btn = gr.Button("Login", elem_classes="green_bg")

    with gr.Column(visible=False) as chat_row:
        logout_btn = gr.Button("Logout", elem_classes="red_bg")
        cb_live = gr.Chatbot(label="Geschiedenis", scale=1, type="messages")
        with gr.Group() as gr_live:
            with gr.Row():
                tb_user = gr.Textbox(
                    show_label=False, placeholder="Stel hier je vraag...", scale=10
                )
                btn_send = gr.Button(
                    "",
                    scale=0,
                    min_width=64,
                    icon=SEND_ICON_PATH,
                    elem_classes="green_bg",
                )
                btn_remove = gr.Button(
                    "",
                    scale=0,
                    min_width=64,
                    icon=DISPOSAL_ICON_PATH,
                    elem_classes="red_bg",
                )

            # Event handlers
            tb_user.submit(append_user, [tb_user, user_info], [cb_live]).then(
                append_ai,
                [tb_user, user_info],
                [tb_user, cb_live],
            )
            btn_send.click(append_user, [tb_user, user_info], [cb_live]).then(
                append_ai,
                [tb_user, user_info],
                [tb_user, cb_live],
            )
            btn_remove.click(clear_log, [user_info], [tb_user, cb_live])

    login_btn.click(
        login,
        inputs=[username, password, user_info],
        outputs=[login_row, chat_row, cb_live, user_info],
    )

# Launch the Gradio app
llm_client_ui.queue().launch(server_name="0.0.0.0", server_port=7862)
