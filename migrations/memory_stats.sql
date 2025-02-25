CREATE OR REPLACE FUNCTION get_memory_stats(p_account_id BIGINT, p_memory_type VARCHAR)
RETURNS TABLE (
    total_messages BIGINT,
    user_messages BIGINT,
    assistant_messages BIGINT,
    oldest_message TIMESTAMP WITH TIME ZONE,
    newest_message TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_messages,
        COUNT(*) FILTER (WHERE role = 'user') as user_messages,
        COUNT(*) FILTER (WHERE role = 'assistant') as assistant_messages,
        MIN(timestamp) as oldest_message,
        MAX(timestamp) as newest_message
    FROM chat_history
    WHERE account_id = p_account_id 
    AND memory_type = p_memory_type;
END;
$$ LANGUAGE plpgsql; 