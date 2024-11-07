import logging
import pandas as pd
import gradio as gr

from services.document_manager import (
    list_documents,
    remove_document,
    add_documents,
    list_collections,
    add_collection,
)

# Constants
EXPLAINER_TEXT = (
    "Upload company or business information here if you want the language model to be able to perform lookup into it. "
    "Do not upload data files. "
    "Processing may take considerable time depending on the size of the document. "
    "Do not interrupt the processing step. There is no undo."
)


def on_select_file(evt: gr.SelectData):
    if isinstance(evt.value, list):
        selected_filename = evt.value[0]
    else:
        selected_filename = evt.value
    logging.info(f"User selected {selected_filename} at {evt.index} from {evt.target}")
    return gr.update(interactive=True), selected_filename


def load_files_list(collection):
    """
    Load files based on the selected collection.
    """
    df = list_documents(
        collection
    )  # Assuming list_documents can take collection as an argument
    return df


def add_new_collection(new_collection, collections_state):
    if new_collection and new_collection not in collections_state:
        add_collection(new_collection)
        collections_state.append(new_collection)
        return (
            gr.update(choices=collections_state, value=new_collection),
            None,
        )  # Reset TextInput
    return (
        gr.update(choices=collections_state, value=new_collection),
        None,
    )


def file_upload_interface():
    selected_file = gr.State()
    gr.HTML(EXPLAINER_TEXT, visible=True)

    with gr.Blocks() as interface:
        gr.Markdown("### Kies een collectie of maak een nieuwe aan")

        collections_state = gr.State(value=list_collections)

        # Voeg een lege optie toe als placeholder
        collection_choices = list_collections()
        default_collection = collection_choices[0] if collection_choices else None

        # Dropdown voor bestaande collecties, met de eerste waarde als standaard
        collection_dropdown = gr.Dropdown(
            choices=collection_choices,
            label="Kies een collectie",
            value=default_collection,  # Eerste collectie standaard geselecteerd
            interactive=True,
        )

        # TextInput voor nieuwe collectie
        new_collection_input = gr.Textbox(
            placeholder="Voer een nieuwe collectie naam in",
            label="Nieuwe collectie aanmaken",
        )

        # Knop om nieuwe collectie toe te voegen
        add_button = gr.Button("Toevoegen")

        # Event voor het toevoegen van een nieuwe collectie
        add_button.click(
            add_new_collection,
            inputs=[new_collection_input, collections_state],
            outputs=[collection_dropdown, new_collection_input],
        )

        # Sectie voor het uploaden van documenten (standaard zichtbaar voor de eerste collectie)
        document_upload = gr.Group(visible=True)
        with document_upload:
            file_upload = gr.File(
                label="Click to Upload (a) File(s)", file_count="multiple", visible=True
            )

            default_files_list = (
                load_files_list(collection_choices[0]) if collection_choices else None
            )

            files_list = gr.Dataframe(
                headers=["Naam"],
                datatype=["str"],
                value=default_files_list,  # Laad documenten voor de eerste collectie
                interactive=False,
            )

            delete_file_button = gr.Button(
                "Delete", interactive=False, elem_classes="red_bg"
            )

            # Define interactions
            files_list.select(
                fn=on_select_file,
                inputs=None,
                outputs=[delete_file_button, selected_file],
            )

            delete_file_button.click(
                remove_document, [selected_file], [files_list], queue=False
            )

            file_upload.upload(
                add_documents, [file_upload, collection_dropdown], [files_list]
            )

        # Update documents based on collection selection
        collection_dropdown.change(
            fn=lambda collection: load_files_list(collection),
            inputs=[collection_dropdown],
            outputs=[files_list],  # Update de lijst met documenten
        )

    return (files_list, file_upload, delete_file_button, load_files_list)


file_upload_interface()
