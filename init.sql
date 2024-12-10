CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    collection VARCHAR(255) NOT NULL,
    summary TEXT,
    CONSTRAINT unique_file_collection UNIQUE (file_name, collection)
);

-- New chat_messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role VARCHAR(10) NOT NULL, -- 'human' or 'AI'
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Toevoegen van een standaardgebruiker aan de 'users' tabel
INSERT INTO users (username, password, role)
VALUES ('philippe', '$2b$12$IpMWh09YcV65iO9I9VfXo.sfo5eQeKfSy3F6CHEPPN6LvWtOO51r.', 'admin');


-- Tabular vectorstore
CREATE EXTENSION IF NOT EXISTS vector;

DROP DATABASE IF EXISTS tabular_documents_db;
CREATE DATABASE tabular_documents_db;
DO $$
DECLARE
    db_name TEXT := 'tabular_documents_db';
BEGIN
    EXECUTE format('DROP SCHEMA IF EXISTS %I CASCADE', db_name);
    EXECUTE format('CREATE SCHEMA %I', db_name);
    
    EXECUTE format('DROP TABLE IF EXISTS %I.tabular_collections', db_name);
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.tabular_collections (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )', db_name);
        
    EXECUTE format('DROP TABLE IF EXISTS %I.tabular_documents', db_name);
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.tabular_documents (
            id BIGSERIAL PRIMARY KEY,
            file_name TEXT NOT NULL UNIQUE,
            file_hash VARCHAR(64) NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_description TEXT,
            file_description_embedding vector(1024),
            file_schema JSONB
        )', db_name)

    EXECUTE format('DROP TABLE IF EXISTS %I.tabular_rows', db_name);
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.tabular_rows (
            id BIGSERIAL PRIMARY KEY,
            file_id BIGINT REFERENCES %I.tabular_documents(id) ON DELETE CASCADE,
            row_embedding vector(1024),
            attributes JSONB
        )', db_name, db_name);
        
    EXECUTE format('DROP TABLE IF EXISTS %I.tabular_documents_collections', db_name);
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.tabular_documents_collections (
            collection_id BIGINT REFERENCES %I.tabular_collections(id) ON DELETE CASCADE,
            document_id BIGINT REFERENCES %I.tabular_documents(id) ON DELETE CASCADE,
            PRIMARY KEY (collection_id, document_id)
        )', db_name, db_name, db_name);
        
END $$;