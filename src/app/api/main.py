from fastapi import FastAPI
from app.api.auth import router as auth_router
from app.api.llm import router as llm_router

app = FastAPI()

# Voeg routes toe
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(llm_router, prefix="/llm", tags=["LLM"])

@app.get("/")
def read_root():
    return {"message": "Welcome to PiXie API"}