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
    session_id VARCHAR(255) DEFAULT '0',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Conversatie Logging tabellen
CREATE TABLE IF NOT EXISTS conversation_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_type VARCHAR(20) NOT NULL, -- 'user_question', 'ai_response', 'system_event'
    content TEXT NOT NULL,
    metadata JSONB, -- Flexibele opslag voor extra informatie
    processing_time_ms INTEGER, -- Tijd voor AI response generatie
    token_count INTEGER, -- Voor kostenbeheer
    collection_used VARCHAR(255), -- Welke kennisbank werd gebruikt
    user_ip VARCHAR(45), -- Voor geografische analyse (optioneel)
    user_agent TEXT, -- Browser/app informatie
    error_occurred BOOLEAN DEFAULT FALSE,
    error_details TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexen voor snelle queries
CREATE INDEX IF NOT EXISTS idx_conversation_logs_session_timestamp ON conversation_logs(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_user_timestamp ON conversation_logs(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_timestamp ON conversation_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_conversation_logs_message_type ON conversation_logs(message_type);

-- Sessie overzicht tabel voor snelle sessie statistieken
CREATE TABLE IF NOT EXISTS conversation_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    total_user_questions INTEGER DEFAULT 0,
    total_ai_responses INTEGER DEFAULT 0,
    avg_response_time_ms FLOAT,
    collections_used TEXT[], -- Array van gebruikte collecties
    session_duration_minutes INTEGER,
    client_info JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_start ON conversation_sessions(user_id, start_time);

-- Toevoegen van een standaardgebruiker aan de 'users' tabel
INSERT INTO users (username, password, role)
VALUES ('philippe', '$2b$12$IpMWh09YcV65iO9I9VfXo.sfo5eQeKfSy3F6CHEPPN6LvWtOO51r.', 'admin');


-- Tabular vectorstore
CREATE EXTENSION IF NOT EXISTS vector;
    
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
    language TEXT,
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