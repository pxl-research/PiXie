import gradio as gr
from app.ui.admin.file_management import file_upload_interface
from app.ui.admin.user_management import user_management_interface
from app.ui.admin.conversation_analytics_ui import create_conversation_analytics_ui
from services.document_manager import (
    list_collections,
)

# Haal de eerste collectie op
collection_choices = list_collections()
default_collection = (
    collection_choices[0] if collection_choices else []
)  # Eerste collectie standaard geselecteerd


def create_admin_ui(admin_app: gr.Blocks) -> None:
    gr.Markdown("# Admin Dashboard")

    with gr.Row():
        btn_manage_users = gr.Button("Manage Users")
        btn_upload_files = gr.Button("Upload Files")
        btn_conversation_analytics = gr.Button("📈 Conversatie Analytics")

    # Sections (initially hidden)
    user_management_section = gr.Column(visible=False)
    file_upload_section = gr.Column(visible=False)
    analytics_section = gr.Column(visible=False)

    # File Upload Section
    with file_upload_section:
        (files_list, file_upload, delete_file_button, load_files_list) = (
            file_upload_interface()
        )

    with user_management_section:
        (users_list, add_user_button, delete_user_button, feedback, load_users_list) = (
            user_management_interface()
        )

    # Conversation Analytics Section
    with analytics_section:
        create_conversation_analytics_ui()

    # Zorg ervoor dat de juiste collectie wordt doorgegeven bij het laden
    admin_app.load(
        fn=lambda: load_files_list(
            default_collection
        ),  # Geeft standaard de eerste collectie door
        inputs=None,
        outputs=files_list,
    )
    admin_app.load(fn=load_users_list, inputs=None, outputs=users_list)

    # Functions to show/hide sections
    def show_user_management():
        return (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    def show_file_upload():
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=False),
        )

    def show_analytics():
        return (
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
        )

    # Button click events
    btn_manage_users.click(
        fn=show_user_management,
        inputs=None,
        outputs=[user_management_section, file_upload_section, analytics_section],
    )

    btn_upload_files.click(
        fn=show_file_upload,
        inputs=None,
        outputs=[user_management_section, file_upload_section, analytics_section],
    )

    btn_conversation_analytics.click(
        fn=show_analytics,
        inputs=None,
        outputs=[user_management_section, file_upload_section, analytics_section],
    )
