import gradio as gr
import logging
from services.authentication.authentication_manager import add_user, delete_user, list_users

def on_select(evt: gr.SelectData):  # SelectData is a subclass of EventData
    logging.info(f"User selected {evt.value} at {evt.index} from {evt.target}")
    return gr.Button(interactive=True), evt.value

def user_management_interface():
    """
    Definieer de gebruikersbeheer interface.

    Returns:
    - gr.Column: De gebruikersbeheer sectie van de Gradio interface.
    """
    with gr.Column() as user_management_section:
        gr.Markdown("## Gebruikersbeheer")
        
        # Sectie voor het toevoegen van een gebruiker
        with gr.Row():
            username = gr.Textbox(label="Gebruikersnaam")
            password = gr.Textbox(label="Wachtwoord", type="password")
        
        add_user_button = gr.Button("Voeg Gebruiker Toe")
        feedback = gr.Markdown("")  # Markdown component voor feedback
        
        users_list = gr.Dataframe(
            headers=["Gebruikersnaam"],
            datatype=["str"],
            value=[[user] for user in list_users()],
            interactive=False
        )
        
        # Sectie voor het verwijderen van een gebruiker
        delete_user_button = gr.Button("Verwijder Gebruiker", interactive=False, elem_classes="red_bg")
        delete_feedback = gr.Markdown("")  # Markdown component voor delete feedback
        
        # State om de geselecteerde gebruiker op te slaan
        selected_user = gr.State()
        
        # Definieer interacties
        
        # Wanneer een gebruiker wordt geselecteerd in de Dataframe, update de geselecteerde gebruiker en activeer de Delete knop
        users_list.select(
            fn=on_select,
            inputs=None,
            outputs=[delete_user_button, selected_user]
        )
        
        # Wanneer de Delete knop wordt geklikt, verwijder de geselecteerde gebruiker
        delete_user_button.click(
            fn=delete_user,
            inputs=[users_list, selected_user],
            outputs=[feedback, users_list],
            queue=False
        )
        
        # Voeg een gebruiker toe en update de gebruikerslijst en reset de selectie
        add_user_button.click(
            fn=add_user,
            inputs=[username, password],
            outputs=[feedback, users_list, selected_user],
            queue=False
        )
    
    return user_management_section