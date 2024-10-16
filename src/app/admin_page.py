import gradio as gr
from file_management import file_upload_interface
from user_management import user_management_interface
from services.authentication.authentication_manager import admin_auth

CSS_STYLES = """
    .red_bg {background: red}
    footer {display:none !important}
"""

with gr.Blocks(css=CSS_STYLES, title="PiXie") as llm_client_ui:
    gr.Markdown("# Admin Dashboard")

    with gr.Row():
        btn_manage_users = gr.Button("Manage Users")
        btn_upload_files = gr.Button("Upload Files")

    # Sections (initially hidden)
    user_management_section = gr.Column(visible=False)
    file_upload_section = gr.Column(visible=False)

    # File Upload Section
    with file_upload_section:
        (files_list, file_upload, delete_file_button, feedback, load_files_list) = (
            file_upload_interface()
        )

    with user_management_section:
        (users_list, add_user_button, delete_user_button, feedback, load_users_list) = (
            user_management_interface()
        )

    llm_client_ui.load(fn=load_files_list, inputs=None, outputs=files_list)
    llm_client_ui.load(fn=load_users_list, inputs=None, outputs=users_list)

    # Functions to show/hide sections
    def show_user_management():
        return gr.update(visible=True), gr.update(visible=False)

    def show_file_upload():
        return gr.update(visible=False), gr.update(visible=True)

    # Button click events
    btn_manage_users.click(
        fn=show_user_management,
        inputs=None,
        outputs=[user_management_section, file_upload_section],
    )

    btn_upload_files.click(
        fn=show_file_upload,
        inputs=None,
        outputs=[user_management_section, file_upload_section],
    )

llm_client_ui.launch(server_name="0.0.0.0", server_port=7861, auth=admin_auth)
