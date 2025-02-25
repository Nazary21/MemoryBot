-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables
CREATE TABLE IF NOT EXISTS accounts (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS temporary_accounts (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    telegram_chat_id BIGINT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS account_chats (
    account_id BIGINT REFERENCES accounts(id),
    telegram_chat_id BIGINT UNIQUE NOT NULL,
    chat_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, telegram_chat_id)
);

CREATE TABLE IF NOT EXISTS chat_history (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    account_id BIGINT REFERENCES accounts(id),
    telegram_chat_id BIGINT,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    memory_type VARCHAR(50) NOT NULL CHECK (memory_type IN ('short_term', 'mid_term', 'whole_history')),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    CONSTRAINT valid_content CHECK (length(content) > 0)
);

CREATE TABLE IF NOT EXISTS account_settings (
    account_id BIGINT REFERENCES accounts(id),
    setting_key VARCHAR(255),
    setting_value JSONB,
    PRIMARY KEY (account_id, setting_key)
);

CREATE TABLE IF NOT EXISTS migration_mapping (
    old_chat_id BIGINT UNIQUE,
    new_account_id BIGINT REFERENCES accounts(id),
    migration_status VARCHAR(50),
    migrated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS history_context (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    account_id BIGINT REFERENCES accounts(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_summary CHECK (length(summary) > 0)
);

-- Add index for history context queries
CREATE INDEX IF NOT EXISTS idx_history_context_account ON history_context(account_id);

-- Add rules table for per-tenant bot rules
CREATE TABLE IF NOT EXISTS bot_rules (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    account_id BIGINT REFERENCES accounts(id) ON DELETE CASCADE,
    rule_text TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_rule CHECK (length(rule_text) > 0)
);

-- Add AI model preferences table
CREATE TABLE IF NOT EXISTS ai_model_settings (
    account_id BIGINT REFERENCES accounts(id) ON DELETE CASCADE,
    model_name VARCHAR(50) NOT NULL,
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_chat_history_account_type ON chat_history(account_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_chat_history_telegram ON chat_history(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_temporary_accounts_chat ON temporary_accounts(telegram_chat_id);

-- Add usage tracking table
CREATE TABLE IF NOT EXISTS usage_stats (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    account_id BIGINT REFERENCES accounts(id) ON DELETE CASCADE,
    tokens_used INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usage_stats_account_time ON usage_stats(account_id, timestamp);

-- Function to get account usage stats
CREATE OR REPLACE FUNCTION get_account_usage_stats(
    p_account_id BIGINT,
    p_start_date TIMESTAMP WITH TIME ZONE,
    p_end_date TIMESTAMP WITH TIME ZONE
) RETURNS TABLE (
    total_tokens BIGINT,
    message_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(tokens_used), 0) as total_tokens,
        COUNT(*) as message_count
    FROM usage_stats
    WHERE account_id = p_account_id
    AND timestamp >= p_start_date
    AND timestamp <= p_end_date;
END;
$$ LANGUAGE plpgsql; 