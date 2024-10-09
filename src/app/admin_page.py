import gradio as gr
from upload import file_upload_interface
from user_management import user_management_interface

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
        upload_section = file_upload_interface()

    # User Management Section (Placeholder)
    with user_management_section:
        user_management = user_management_interface()

    # Functions to show/hide sections
    def show_user_management():
        return gr.update(visible=True), gr.update(visible=False)

    def show_file_upload():
        return gr.update(visible=False), gr.update(visible=True)

    # Button click events
    btn_manage_users.click(
        fn=show_user_management,
        inputs=None,
        outputs=[user_management_section, file_upload_section]
    )

    btn_upload_files.click(
        fn=show_file_upload,
        inputs=None,
        outputs=[user_management_section, file_upload_section]
    )

llm_client_ui.launch(server_name="0.0.0.0", server_port=7861)