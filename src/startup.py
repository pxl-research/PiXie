from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import gradio as gr
from app.ui.admin.admin_page import create_admin_ui
from app.ui.chat.chat import create_chat_ui
from services.authentication.authentication_manager import custom_auth, admin_auth
from app.api.auth import auth_router, limiter as auth_limiter
from app.api.llm import chat_router
from services.agent_service import init_mcp_agent

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

app = FastAPI()

# Rate limiter configuratie
app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuratie voor security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8111", "http://127.0.0.1:8111"],  # Alleen lokale toegang
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Beperkte HTTP methods
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await init_mcp_agent()


# Voeg routes toe
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/v1", tags=["AI"])


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
# uvicorn src.startup:app --host 0.0.0.0 --port 8000
