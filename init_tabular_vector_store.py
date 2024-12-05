# TODO: call from somewhere in Dockerfile or Docker compose when integrating into Pixie
# Might also want to convert this to a .sql file if easier for creating a volume
# This could be included into init.sql.
"""
This script sets up a PostgreSQL database schema for managing
tabular documents, the collections they belong to and their associated metadata. 
It uses psycopg2 to connect to the PostgreSQL database 
and pgvector for embedding vectors. 

It connects to a PostgreSQL database using credentials 
provided via environment variables.

It ensures the vector extension (used for vector operations) 
is installed and registers it with the database connection.

The script can be executed multiple times, since it 
drops tables if they already exist.
It also drops any existing schema with the same name
and initializes a fresh schema.

It implements `ON DELETE CASCADE` to ensure dependent data 
is cleaned up when a referenced entry is deleted.

It catches any database errors during the schema creation process 
and rolls back the transaction if an error occurs and logs the details.

Finally, it closes all the connections.

Tables:
   - tabular_collections: Manages collections of tabular documents with unique names.
   - tabular_documents: Document metadata, including file details, 
       embeddings (as vectors) and JSON schemas.
   - tabular_rows: Contains row-level data linked to documents, 
       including row embeddings and attributes stored as JSON.
   - tabular_documents_collections: Many-to-many relationships between
       collections and documents. A collection can have multiple documents
       and a document can belong to multiple collections.
"""

import os
import logging
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json, execute_values

conn = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host="db",  # "localhost"
    port="5432",
)
conn.autocommit = True

with conn.cursor() as c:
    try:
        c.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(c)
        db_name = "tabular_documents_db"
        c.execute(f"DROP DATABASE IF EXISTS {db_name}")
        c.execute(f"CREATE DATABASE {db_name}")
        c.execute(f"DROP SCHEMA IF EXISTS {db_name} CASCADE")
        c.execute(f"CREATE SCHEMA {db_name}")

        c.execute(f"DROP TABLE IF EXISTS {db_name}.tabular_collections")
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {db_name}.tabular_collections (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
        """
        )

        c.execute(f"DROP TABLE IF EXISTS {db_name}.tabular_documents")
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {db_name}.tabular_documents (
                id BIGSERIAL PRIMARY KEY,
                file_name TEXT NOT NULL UNIQUE,
                file_hash VARCHAR(64) NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_description TEXT,
                file_description_embedding vector(1024),
                file_schema JSONB
            );
        """
        )

        c.execute(f"DROP TABLE IF EXISTS {db_name}.tabular_rows")
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {db_name}.tabular_rows (
                id BIGSERIAL PRIMARY KEY,
                file_id BIGINT REFERENCES {db_name}.tabular_documents(id) ON DELETE CASCADE,
                row_embedding vector(1024),
                attributes JSONB
            );
        """
        )

        c.execute(f"DROP TABLE IF EXISTS {db_name}.tabular_documents_collections")
        c.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {db_name}.tabular_documents_collections (
                collection_id BIGINT REFERENCES {db_name}.tabular_collections(id) ON DELETE CASCADE,
                document_id BIGINT REFERENCES {db_name}.tabular_documents(id) ON DELETE CASCADE,
                PRIMARY KEY (collection_id, document_id)
            );
        """
        )

        conn.commit()
    except psycopg2.DatabaseError as e:
        conn.rollback()
        logging.error("Error: ", e)
    finally:
        conn.close()
