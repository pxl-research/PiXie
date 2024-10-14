import gradio as gr
import bcrypt
import json
import os
import logging

USERS_PATH = "src/assets/helper/users.json"


def load_users():
    """
    Laad de gebruikers vanuit het JSON-bestand.

    Returns:
    - dict: Een dictionary met gebruikersnamen als sleutels en gehashte wachtwoorden als waarden.
    """
    if os.path.exists(USERS_PATH) and os.path.getsize(USERS_PATH) > 0:
        try:
            with open(USERS_PATH, "r") as f:
                users = json.load(f)
                return users
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")
            return {}
    else:
        # Maak een standaard admin gebruiker aan
        default_admin = {
            "admin": {
                "password": bcrypt.hashpw(
                    "admin".encode("utf-8"), bcrypt.gensalt()
                ).decode("utf-8"),
                "role": "admin",
            }
        }
        save_users(default_admin)
        logging.info("Standaard admin gebruiker aangemaakt.")
        return default_admin


def save_users(users):
    """
    Sla de gebruikers op in het JSON-bestand.

    Parameters:
    - users: dict
        Een dictionary met gebruikersnamen en gehashte wachtwoorden.
    """
    with open(USERS_PATH, "w") as f:
        json.dump(users, f, indent=4)


def add_user(username, password, role="user"):
    """
    Voeg een nieuwe gebruiker toe.
    Parameters:
        username (str): De gebruikersnaam van de nieuwe gebruiker.
        password (str): Het wachtwoord van de nieuwe gebruiker.
        role (str): De rol van de nieuwe gebruiker. Standaard is "user".
    Returns:
        tuple: Feedback bericht, bijgewerkte gebruikerslijst, reset selectie.
    """
    users = load_users()

    if username in users:
        logging.info(f"User {username} already exists.")
        message = f"<span style='color: red;'>Gebruiker '{username}' bestaat al.</span>"
        return message, [[user] for user in users.keys()], None

    # Hash het wachtwoord met bcrypt
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
    users[username] = {"password": hashed_pw, "role": role}
    save_users(users)

    logging.info(f"User {username} added successfully.")
    message = f"<span style='color: green;'>Gebruiker '{username}' is succesvol toegevoegd.</span>"
    return message, [[user] for user in users.keys()], None


def delete_user(user_list: gr.Dataframe, selected_user: str):
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

    users = load_users()

    if selected_user in users:
        del users[selected_user]
        save_users(users)
        logging.info(f"User {selected_user} deleted successfully.")
        message = f"<span style='color: green;'>Gebruiker '{selected_user}' is succesvol verwijderd.</span>"
        user_list = user_list[user_list.iloc[:, 0] != selected_user]
        return message, [[user] for user in users.keys()]


def list_users():
    """
    Haal de huidige lijst van gebruikers op.

    Returns:
    - list: Een lijst met gebruikersnamen.
    """
    users = load_users()
    return list(users.keys())


# Aangepaste authenticatiefunctie
def custom_auth(username, password):
    users = load_users()
    hashed_pw = users.get(username)
    if hashed_pw:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_pw.encode("utf-8"))
    else:
        return False


def admin_auth(username, password):
    users = load_users()
    hashed_pw = users.get(username).get("password")
    if hashed_pw:
        return (
            bcrypt.checkpw(password.encode("utf-8"), hashed_pw.encode("utf-8"))
            and users[username]["role"] == "admin"
        )
    else:
        return False
