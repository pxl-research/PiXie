import os
import gradio as gr
from app.ui.chat.blocks_llm_chat_with_rag import (
    append_user,
    append_ai,
    clear_log,
)
from services.authentication.authentication_manager import custom_auth
from services.chat_history.chat_history_manager import get_chat_history
from services.document_manager import list_collections
from services.database.user_db_operations import get_user_by_username
from typing import List, Tuple, Optional, Dict, Any

# Constants
CSS_STYLES = """
    .red_bg {background: red}
    .green_bg {background: green}
    footer {display:none !important}
"""
SEND_ICON_PATH = os.path.join("src", "assets", "icons", "send.png")
DISPOSAL_ICON_PATH = os.path.join("src", "assets", "icons", "disposal.png")

collection_choices = list_collections()


def load_chat_history(user_info: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Load chat history for a specific user.

    This function retrieves the chat history for a user from the database, using the user ID.
    It limits the number of messages to the 10 most recent messages.

    Parameters:
    - user_info: Optional[Dict[str, Any]]
        A dictionary containing the user information, including the user ID.

    Returns:
    - List[Dict[str, str]]: A list of dictionaries representing the chat history, with 'role' and 'content' keys.
    """
    if user_info and "id" in user_info:
        user_id = user_info["id"]
        chat_history = get_chat_history(user_id, limit=10)
        return chat_history
    return []


def login(request: gr.Request) -> Tuple[List[Dict[str, str]], Optional[Dict[str, Any]]]:
    """
    Load chat history for a specific user.

    This function retrieves the chat history for a user from the database, using the user ID.
    It limits the number of messages to the 10 most recent messages.

    Parameters:
    - request: gr.Request
        The Gradio request object containing username information.

    Returns:
    - Tuple[List[Dict[str, str]], Optional[Dict[str, Any]]]: A tuple containing:
        - The chat history as a list of dictionaries with 'role' and 'content' keys
        - The user information dictionary or None if user not found
    """
    username = request.username
    user_info = get_user_by_username(username)
    user_id = user_info["id"] if user_info else None
    chat_history = get_chat_history(user_id, limit=10)
    return chat_history, user_info


# Gradio UI Setup
with gr.Blocks(fill_height=True, title="PiXie", css=CSS_STYLES) as llm_client_ui:
    user_info = gr.State(value=None)

    gr.Markdown("# <center>Vraag het aan PiXie</center>")

    # Chat section
    with gr.Column() as chat_row:
        logout_btn = gr.Button("Logout", link="/logout", elem_classes="red_bg")
        cb_live = gr.Chatbot(label="Geschiedenis", scale=1, type="messages")
        with gr.Row(equal_height=True, elem_classes="container"):
            collection_dropdown = gr.Dropdown(
                choices=collection_choices,
                label="Kies een collectie",
                value=collection_choices[0],
                interactive=True,
            )

            tb_user = gr.Textbox(
                show_label=False, placeholder="Stel hier je vraag...", scale=10
            )

            with gr.Column(elem_classes="buttons"):
                btn_send = gr.Button(
                    value="Verstuur",
                    icon=SEND_ICON_PATH,
                    elem_classes="green_bg",
                )
                btn_remove = gr.Button(
                    value="Verwijder geschiedenis",
                    icon=DISPOSAL_ICON_PATH,
                    elem_classes="red_bg",
                )

            # Event handlers for chat
            tb_user.submit(append_user, [tb_user, user_info], [cb_live]).then(
                append_ai,
                [collection_dropdown, tb_user, user_info],
                [tb_user, cb_live],
            )
            btn_send.click(append_user, [tb_user, user_info], [cb_live]).then(
                append_ai,
                [collection_dropdown, tb_user, user_info],
                [tb_user, cb_live],
            )
            btn_remove.click(clear_log, [user_info], [tb_user, cb_live])

    llm_client_ui.load(
        fn=login,
        inputs=None,
        outputs=[cb_live, user_info],
    )

# Launch the Gradio app
llm_client_ui.queue().launch(server_name="0.0.0.0", server_port=7862, auth=custom_auth)
