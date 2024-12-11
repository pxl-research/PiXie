import gradio as gr
import pandas as pd
import logging
from services.authentication.authentication_manager import (
    add_user,
    delete_user,
    list_users,
)


def on_select_user(evt: gr.SelectData):
    if isinstance(evt.value, list):
        selected_username = evt.value[0]
    else:
        selected_username = evt.value
    logging.info(f"User selected {selected_username} at {evt.index} from {evt.target}")
    return gr.update(interactive=True), selected_username


def user_management_interface():
    """
    Definieer de gebruikersbeheer interface.

    Returns:
    - gr.Column: De gebruikersbeheer sectie van de Gradio interface.
    """
    selected_user = gr.State()
    gr.Markdown("## Gebruikersbeheer")

    # Sectie voor het toevoegen van een gebruiker
    with gr.Row():
        username = gr.Textbox(label="Gebruikersnaam")
        password = gr.Textbox(label="Wachtwoord", type="password")
        role = gr.Dropdown(label="Rol", choices=["user", "admin"], value="user")

    add_user_button = gr.Button("Voeg Gebruiker Toe")
    feedback = gr.Markdown("")  # Markdown component voor feedback

    users_list = gr.Dataframe(
        headers=["Gebruikersnaam"],
        datatype=["str"],
        value=list_users(),
        interactive=False,
    )

    # Sectie voor het verwijderen van een gebruiker
    delete_user_button = gr.Button(
        "Verwijder Gebruiker", interactive=False, elem_classes="red_bg"
    )

    # Definieer interacties

    # Wanneer een gebruiker wordt geselecteerd in de Dataframe, update de geselecteerde gebruiker en activeer de Delete knop
    users_list.select(
        fn=on_select_user, inputs=None, outputs=[delete_user_button, selected_user]
    )

    # Wanneer de Delete knop wordt geklikt, verwijder de geselecteerde gebruiker
    delete_user_button.click(
        fn=delete_user,
        inputs=[selected_user],
        outputs=[feedback, users_list],
        queue=False,
    )

    # Voeg een gebruiker toe en update de gebruikerslijst en reset de selectie
    add_user_button.click(
        fn=add_user,
        inputs=[username, password, role],
        outputs=[feedback, users_list, selected_user],
        queue=False,
    )

    # Functie om de gebruikerslijst te laden
    def load_users_list():
        df = list_users()
        return df

    # Retourneer de componenten en functies die nodig zijn
    return (users_list, add_user_button, delete_user_button, feedback, load_users_list)
