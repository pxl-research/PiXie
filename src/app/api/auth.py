from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import timedelta
from services.authentication.authentication_manager import (
    create_access_token,
    decode_access_token,
    verify_password,
    hash_password,
    oauth2_scheme,
)
from services.database.user_db_operations import (
    get_user_by_username,
    add_user_to_db,
    user_exists,
)

from pydantic import BaseModel
import os


# Maak een Pydantic-model voor de request body
class RegisterUser(BaseModel):
    username: str
    password: str
    role: str = "user"


# Rate limiter configuratie (wordt geconfigureerd in startup.py)
limiter = Limiter(key_func=get_remote_address)
auth_router = APIRouter()


@auth_router.post("/token")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login route die een JWT access token retourneert.

    Args:
        form_data (OAuth2PasswordRequestForm): Bevat gebruikersnaam en wachtwoord.

    Returns:
        dict: Access token en token type.
    """
    username = form_data.username
    password = form_data.password

    user = get_user_by_username(username=username)
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(
            minutes=float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
        ),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/register")
@limiter.limit("3/minute")  # Max 3 registrations per minute
def register(request: Request, user_data: RegisterUser):
    """
    Registreer een nieuwe gebruiker.

    Args:
        username (str): De gebruikersnaam.
        password (str): Het wachtwoord.
        role (str): De rol van de gebruiker (standaard: 'user').

    Returns:
        dict: Succesbericht.
    """
    if user_exists(username=user_data.username):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_password = hash_password(user_data.password)
    success = add_user_to_db(
        username=user_data.username,
        hashed_password=hashed_password,
        role=user_data.role,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to register user")

    return {"message": f"User '{user_data.username}' successfully registered"}


@auth_router.get("/me")
def get_current_user(
    token: str = Depends(oauth2_scheme),
):
    """
    Beveiligde route om huidige gebruiker en rol op te halen.

    Args:
        token (str): Het JWT-token, automatisch opgehaald via OAuth2PasswordBearer.

    Returns:
        dict: Gebruikersinformatie uit het token.
    """
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user_by_username(username=username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"username": user["username"], "role": user["role"], "id": user["id"]}
