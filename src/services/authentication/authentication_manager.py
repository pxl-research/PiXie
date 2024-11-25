import os
import bcrypt
import logging
from services.database.user_db_operations import (
    get_all_users,
    add_user_to_db,
    delete_user_from_db,
    user_exists,
    get_user,
    get_user_by_username,
)
import pandas as pd
from typing import List, Optional, Dict, Any
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def add_user(username, password, role="user"):
    """
    Voegt een nieuwe gebruiker toe via de interface.

    Parameters:
        username (str): De gebruikersnaam van de nieuwe gebruiker.
        password (str): Het wachtwoord van de nieuwe gebruiker.
        role (str): De rol van de nieuwe gebruiker.

    Returns:
        tuple: Feedbackbericht, bijgewerkte gebruikerslijst, reset selectie.
    """
    if user_exists(username):
        logging.info(f"Gebruiker {username} bestaat al.")
        message = f"<span style='color: red;'>Gebruiker '{username}' bestaat al.</span>"

        # Haal de bijgewerkte gebruikerslijst op
        users_list = [[user] for user in get_all_users()]
        users_df = pd.DataFrame(users_list, columns=["Gebruikersnaam"])
        return message, users_df, None

    # Hash het wachtwoord met bcrypt
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    # Voeg de gebruiker toe aan de database
    success = add_user_to_db(username, hashed_pw, role)
    if success:
        logging.info(f"Gebruiker {username} succesvol toegevoegd.")
        message = f"<span style='color: green;'>Gebruiker '{username}' is succesvol toegevoegd.</span>"
    else:
        logging.error(f"Fout bij het toevoegen van gebruiker {username}.")
        message = f"<span style='color: red;'>Er is een fout opgetreden bij het toevoegen van gebruiker '{username}'.</span>"

    # Haal de bijgewerkte gebruikerslijst op
    users_list = [[user] for user in get_all_users()]
    users_df = pd.DataFrame(users_list, columns=["Gebruikersnaam"])
    return message, users_df, None


def delete_user(selected_user: str):
    """
    Verwijder een bestaande gebruiker.

    Parameters:
    - selected_user: str
        De gebruikersnaam van de gebruiker die verwijderd moet worden.

    Returns:
    - tuple:
        - str: Een HTML bericht over het resultaat van de verwijdering.
        - list: De bijgewerkte lijst van gebruikers in het juiste formaat (lijst van lijsten).
        - None: Om de geselecteerde gebruiker te resetten.
    """
    if selected_user:
        success = delete_user_from_db(selected_user)
        if success:
            feedback_text = f"Gebruiker '{selected_user}' is succesvol verwijderd."
        else:
            feedback_text = f"Kon gebruiker '{selected_user}' niet verwijderen."
    else:
        feedback_text = "Geen gebruiker geselecteerd."

    # Haal de bijgewerkte gebruikerslijst op
    users = [[user] for user in get_all_users()]
    users_df = pd.DataFrame(users, columns=["Gebruikersnaam"])
    return feedback_text, users_df


def list_users() -> List[List[str]]:
    """
    Haal de huidige lijst van gebruikers op.

    Returns:
    - list: Een lijst met gebruikersnamen.
    """
    user_list = get_all_users()
    user_names = [[username] for username in user_list]
    logging.info("User list retrieved.")
    return user_names


def custom_auth(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticeer een gebruiker met de gegeven gebruikersnaam en wachtwoord.

    Parameters:
        username (str): De gebruikersnaam van de gebruiker.
        password (str): Het wachtwoord van de gebruiker.

    Returns:
        Optional[Dict[str, Any]]: Gebruikersinformatie als authenticatie succesvol is, anders None.
    """
    user = get_user_by_username(username)
    if user and verify_password(password, user['password']):
        logging.info(f"User '{username}' authenticated successfully.")
        return {
            "id": user['id'],
            "username": user['username'],
            "role": user['role']
        }
    else:
        logging.warning(f"Authentication failed for user '{username}'.")
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifieer een plain text wachtwoord tegen het gehashte wachtwoord.

    Parameters:
        plain_password (str): Het plain text wachtwoord.
        hashed_password (str): Het gehashte wachtwoord uit de database.

    Returns:
        bool: True als het wachtwoord overeenkomt, anders False.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def admin_auth(username, password):
    user = get_user(username)
    if user:
        hashed_pw = user.get("password")
        return (
            bcrypt.checkpw(password.encode("utf-8"), hashed_pw.encode("utf-8"))
            and user.get("role") == "admin"
        )
    else:
        return False
    

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Genereert een JWT access token.

    Args:
        data (dict): De payload die in het token wordt opgenomen.
        expires_delta (timedelta, optional): De tijd tot het token verloopt.

    Returns:
        str: Het JWT-token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodeert en verifieert een JWT-token.

    Args:
        token (str): Het JWT-token.

    Returns:
        Dict[str, Any]: De payload van het token als het geldig is.

    Raises:
        HTTPException: Als het token ongeldig is of is verlopen.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Token expired")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Verifieert het token en retourneert de gebruikersinformatie.

    Args:
        token (str): Het JWT-token, automatisch opgehaald via OAuth2PasswordBearer.

    Returns:
        Dict[str, Any]: Gebruikersinformatie uit het token.
    """
    payload = decode_access_token(token)
    return payload
