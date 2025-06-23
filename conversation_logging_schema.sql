-- Conversatie Logging Schema
-- Deze tabel slaat gestructureerde conversatie data op voor analyse

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
