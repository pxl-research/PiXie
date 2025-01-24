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

CREATE EXTENSION IF NOT EXISTS pg_trgm;
    
DROP TABLE IF EXISTS tabular_collections;
CREATE TABLE IF NOT EXISTS tabular_collections (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

DROP TABLE IF EXISTS tabular_documents;
CREATE TABLE IF NOT EXISTS tabular_documents (
    id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL UNIQUE,
    file_hash VARCHAR(64) NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_description TEXT,
    file_description_embedding vector(1024),
    file_schema JSONB
);

DROP TABLE IF EXISTS tabular_rows;
CREATE TABLE IF NOT EXISTS tabular_rows (
    id BIGSERIAL PRIMARY KEY,
    file_id BIGINT REFERENCES tabular_documents(id) ON DELETE CASCADE,
    row_embedding vector(1024),
    attributes JSONB
);
        
DROP TABLE IF EXISTS tabular_documents_collections;
CREATE TABLE IF NOT EXISTS tabular_documents_collections (
    collection_id BIGINT REFERENCES tabular_collections(id) ON DELETE CASCADE,
    document_id BIGINT REFERENCES tabular_documents(id) ON DELETE CASCADE,
    PRIMARY KEY (collection_id, document_id)
);