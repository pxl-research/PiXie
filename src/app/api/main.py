from fastapi import FastAPI
from app.api.auth import router as auth_router

app = FastAPI()

# Voeg routes toe
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

@app.get("/")
def read_root():
    return {"message": "Welcome to PiXie API"}