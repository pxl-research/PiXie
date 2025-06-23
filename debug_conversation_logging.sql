-- Debug query om conversation logging te analyseren
-- Voer deze uit om te zien wat er werkelijk in de database staat

-- 1. Check welke message types we hebben
SELECT message_type, COUNT(*) as count 
FROM conversation_logs 
GROUP BY message_type 
ORDER BY count DESC;

-- 2. Check de laatste 10 log entries
SELECT 
    session_id,
    user_id,
    message_type,
    LEFT(content, 50) as content_preview,
    timestamp,
    collection_used,
    processing_time_ms
FROM conversation_logs 
ORDER BY timestamp DESC 
LIMIT 10;

-- 3. Check conversation sessions
SELECT 
    session_id,
    user_id,
    total_messages,
    total_user_questions,
    total_ai_responses,
    avg_response_time_ms,
    collections_used,
    start_time,
    end_time
FROM conversation_sessions 
ORDER BY start_time DESC 
LIMIT 5;

-- 4. Check of er mismatches zijn tussen logs en sessions
SELECT 
    cl.session_id,
    COUNT(*) as actual_messages,
    COUNT(CASE WHEN cl.message_type = 'user_question' THEN 1 END) as actual_questions,
    COUNT(CASE WHEN cl.message_type = 'ai_response' THEN 1 END) as actual_responses,
    cs.total_messages as recorded_messages,
    cs.total_user_questions as recorded_questions,
    cs.total_ai_responses as recorded_responses
FROM conversation_logs cl
LEFT JOIN conversation_sessions cs ON cl.session_id = cs.session_id
GROUP BY cl.session_id, cs.total_messages, cs.total_user_questions, cs.total_ai_responses
ORDER BY cl.session_id;
