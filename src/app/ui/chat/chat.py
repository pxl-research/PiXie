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


def login(
    username: str, password: str, user_state: Optional[Dict[str, Any]] = None
) -> Tuple[
    gr.update, gr.update, Optional[List[Dict[str, str]]], Optional[Dict[str, Any]]
]:
    """
    Authenticate the user and store user information in the state.

    Parameters:
    - username: str
        The username provided by the user.
    - password: str
        The password provided by the user.
    - user_state: Optional[Dict[str, Any]], optional
        The current user state (not actively used in this implementation).

    Returns:
    - Tuple[gr.update, gr.update, Optional[List[Dict[str, str]]], Optional[Dict[str, Any]]]:
        - gr.update: Used to hide the login form.
        - gr.update: Used to show the chat interface.
        - Optional[List[Dict[str, str]]]: The chat history if the login is successful, otherwise None.
        - Optional[Dict[str, Any]]: The authenticated user information, or None if authentication fails.
    """
    user = custom_auth(username, password)
    if user:
        chatbot = load_chat_history(user)
        return gr.update(visible=False), gr.update(visible=True), chatbot, user
    else:
        return gr.update(visible=True), gr.update(visible=False), None


def logout(user_info: Dict[str, Any]) -> Tuple[gr.update, gr.update, None, None]:
    """
    Log the user out by clearing the session and resetting the interface.

    Parameters:
    - user_info: Dict[str, Any]
        A dictionary containing the current user information, which will be cleared to log the user out.

    Returns:
    - Tuple[gr.update, gr.update, None, None]:
        - gr.update: Used to show the login form.
        - gr.update: Used to hide the chat interface.
        - None: Clears the chat history interface.
        - None: Resets the user information.
    """
    user_info.clear()
    return gr.update(visible=True), gr.update(visible=False), None, None


# Gradio UI Setup
with gr.Blocks(fill_height=True, title="PiXie", css=CSS_STYLES) as llm_client_ui:
    user_info = gr.State(value=None)
    chat_history_state = gr.State(value=[])

    gr.Markdown("# <center>Vraag het aan PiXie</center>")

    # Login section
    with gr.Column(visible=True) as login_row:
        with gr.Row(visible=True):
            username = gr.Textbox(label="Username", placeholder="Enter your username")
            password = gr.Textbox(
                label="Password", placeholder="Enter your password", type="password"
            )
        login_btn = gr.Button("Login", elem_classes="green_bg")

    # Chat section
    with gr.Column(visible=False) as chat_row:
        logout_btn = gr.Button("Logout", elem_classes="red_bg")
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
                    icon=SEND_ICON_PATH,
                    elem_classes="green_bg",
                )
                btn_remove = gr.Button(
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

            # Logout button event handler
            logout_btn.click(
                logout,
                inputs=[user_info],
                outputs=[login_row, chat_row, cb_live, user_info],
            )

    # Login button event handler
    login_btn.click(
        login,
        inputs=[username, password, user_info],
        outputs=[login_row, chat_row, cb_live, user_info],
    )

# Launch the Gradio app
llm_client_ui.queue().launch(server_name="0.0.0.0", server_port=7862)
