from services.database.database import get_db_connection
import logging
from typing import List, Optional, Dict, Any


logger = logging.getLogger(__name__)


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
        logger.debug(f"Deleting user from database: {username}")
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            conn.commit()
            logger.info(f"User deleted successfully: {username}")
            return True
    except Exception as e:
        logger.error(f"Error deleting user {username}: {e}", exc_info=True)
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
        logger.debug(f"Checking if user exists: {username}")
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            exists = cursor.fetchone() is not None
            logger.debug(
                f"User existence check result - username: {username}, exists: {exists}"
            )
            return exists
    except Exception as e:
        logger.error(f"Error checking if user {username} exists: {e}", exc_info=True)
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
        logger.debug(f"Adding user to database - username: {username}, role: {role}")
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, hashed_password, role),
            )
            conn.commit()
            logger.info(f"User added successfully - username: {username}, role: {role}")
            return True
    except Exception as e:
        logger.error(f"Error adding user {username} to database: {e}", exc_info=True)
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
        logger.debug("Retrieving all users from database")
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM users")
            users = cursor.fetchall()
            usernames = [user[0] for user in users]
            logger.info(f"Retrieved all users - count: {len(usernames)}")
            return usernames
    except Exception as e:
        logger.error(f"Error retrieving all users: {e}", exc_info=True)
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
        logger.debug(f"Retrieving user details: {username}")
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
                logger.debug(f"User details retrieved successfully: {username}")
                return user_data
            else:
                logger.debug(f"User not found: {username}")
                return None
    except Exception as e:
        logger.error(f"Error retrieving user {username}: {e}", exc_info=True)
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
        logger.debug(f"Retrieving user by username: {username}")
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, role, password FROM users WHERE username = %s",
                (username,),
            )
            user = cursor.fetchone()
            if user:
                user_data = {
                    "id": user[0],
                    "username": user[1],
                    "role": user[2],
                    "password": user[3],
                }
                logger.debug(f"User retrieved by username successfully: {username}")
                return user_data
            logger.debug(f"User not found by username: {username}")
            return None
    except Exception as e:
        logger.error(
            f"Error retrieving user by username {username}: {e}", exc_info=True
        )
        return None
    finally:
        conn.close()
