from services.database.database import get_db_connection
import logging
from typing import List, Optional, Dict, Any


def delete_user_from_db(username: str) -> bool:
    """
    Remove a user from the 'users' table in the PostgreSQL database.

    This function deletes a user with the specified username from the database.

    Parameters:
        username (str): The username of the user to remove.

    Returns:
        bool: True if the user was successfully removed, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            conn.commit()
            logging.info(f"User '{username}' successfully removed.")
            return True
    except Exception as e:
        logging.error(f"Error removing user '{username}': {e}")
        return False
    finally:
        conn.close()


def user_exists(username: str) -> bool:
    """
    Check if a user already exists in the database.

    This function queries the 'users' table in the PostgreSQL database to verify
    if a user with the specified username exists.

    Parameters:
        username (str): The username to check.

    Returns:
        bool: True if the user exists, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            return cursor.fetchone() is not None
    except Exception as e:
        logging.error(f"Error checking if user exists: {e}")
        return False
    finally:
        conn.close()


def add_user_to_db(username: str, hashed_password: str, role: str) -> bool:
    """
    Add a new user to the database.

    This function inserts a new user record into the 'users' table in the PostgreSQL database.

    Parameters:
        username (str): The username of the new user.
        hashed_password (str): The hashed password of the new user.
        role (str): The role of the new user.

    Returns:
        bool: True if the user was successfully added, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, hashed_password, role),
            )
            conn.commit()
            logging.info(f"User '{username}' successfully added to the database.")
            return True
    except Exception as e:
        logging.error(f"Error adding user to the database: {e}")
        return False
    finally:
        conn.close()


def get_all_users() -> List[str]:
    """
    Retrieve all users from the database.

    This function queries the 'users' table in the PostgreSQL database and retrieves
    all usernames.

    Returns:
        List[str]: A list of usernames.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM users")
            users = cursor.fetchall()
            return [user[0] for user in users]
    except Exception as e:
        logging.error(f"Error retrieving users: {e}")
        return []
    finally:
        conn.close()


def get_user(username: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user details for a given username from the database.

    This function fetches the username, hashed password, and role of a user from the 'users' table.

    Parameters:
        username (str): The username to retrieve.

    Returns:
        Optional[Dict[str, Any]]: A dictionary with keys 'username', 'password', 'role', or None if user not found.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT username, password, role FROM users WHERE username = %s",
                (username,),
            )
            result = cursor.fetchone()
            if result:
                user_data = {
                    "username": result[0],
                    "password": result[1],
                    "role": result[2],
                }
                return user_data
            else:
                return None
    except Exception as e:
        logging.error(f"Error fetching user '{username}': {e}")
        return None
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Haal een gebruiker op basis van de gebruikersnaam uit de database.

    Parameters:
        username (str): De gebruikersnaam van de gebruiker.

    Returns:
        Optional[Dict[str, Any]]: Een dictionary met gebruikersinformatie als de gebruiker bestaat, anders None.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, role, password FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
            if user:
                return {
                    "id": user[0],
                    "username": user[1],
                    "role": user[2],
                    "password": user[3]
                }
            return None
    except Exception as e:
        logging.error(f"Fout bij het ophalen van gebruiker '{username}': {e}")
        return None
    finally:
        conn.close()