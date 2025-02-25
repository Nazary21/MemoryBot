-- Function to get total message count
CREATE OR REPLACE FUNCTION get_total_message_count()
RETURNS BIGINT AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM chat_history);
END;
$$ LANGUAGE plpgsql;

-- Function to get active users count
CREATE OR REPLACE FUNCTION get_active_users_count(p_days INTEGER)
RETURNS BIGINT AS $$
BEGIN
    RETURN (
        SELECT COUNT(DISTINCT account_id)
        FROM chat_history
        WHERE timestamp > NOW() - (p_days || ' days')::INTERVAL
    );
END;
$$ LANGUAGE plpgsql;

-- Function to migrate chat history
CREATE OR REPLACE FUNCTION migrate_chat_history(
    p_temp_account_id BIGINT,
    p_new_account_id BIGINT
) RETURNS VOID AS $$
BEGIN
    -- Move chat history
    UPDATE chat_history
    SET account_id = p_new_account_id
    WHERE account_id = p_temp_account_id;
END;
$$ LANGUAGE plpgsql; 