import psycopg2
import os


def get_db_connection() -> psycopg2.extensions.connection:
    """
    Establish and return a connection to the PostgreSQL database.

    The connection parameters are retrieved from environment variables.

    Returns:
        psycopg2.extensions.connection: A connection object to the PostgreSQL database.
    """
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host="db",
        port="5432",
    )
