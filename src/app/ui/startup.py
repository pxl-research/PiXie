from fastapi import FastAPI
import gradio as gr
from app.ui.admin.admin_page import create_admin_ui
from app.ui.chat.chat import create_chat_ui
from services.authentication.authentication_manager import custom_auth, admin_auth

app = FastAPI()

CSS_STYLES = """
    html, body {
        height: 100%;
        margin: 0;
        padding: 0;
    }

    .gradio-container, gradio-app, .main, #root {
        height: 100% !important;
        min-height: 100% !important;
        display: flex;
        flex-direction: column;
    }
    .red_bg {background: red}
    .green_bg {background: green}
    footer {display:none !important}
"""

# Admin interface
with gr.Blocks(css=CSS_STYLES, fill_height=True, title="PiXie Admin") as admin_ui:
    create_admin_ui(admin_ui)

# Chat interface
with gr.Blocks(css=CSS_STYLES, fill_height=True, title="PiXie Chat") as chat_ui:
    create_chat_ui(chat_ui)

# Mount beide interfaces op verschillende paden
app = gr.mount_gradio_app(app, admin_ui, path="/admin", auth=admin_auth)
app = gr.mount_gradio_app(app, chat_ui, path="/chat", auth=custom_auth)

# Start de server met:
# uvicorn src.app.ui.startup:app --host 0.0.0.0 --port 8000
