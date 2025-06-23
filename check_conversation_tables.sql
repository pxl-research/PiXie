-- Quick check om te zien of conversation tables bestaan
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'conversation%';

-- Als de tabellen bestaan, check de inhoud
SELECT 
    (SELECT COUNT(*) FROM conversation_sessions) as session_count,
    (SELECT COUNT(*) FROM conversation_logs) as log_count;
