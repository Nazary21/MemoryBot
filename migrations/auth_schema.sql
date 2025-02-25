-- Add Supabase user ID to accounts
ALTER TABLE accounts 
ADD COLUMN supabase_user_id UUID UNIQUE,
ADD COLUMN email VARCHAR(255);

-- Create index for Supabase user lookup
CREATE INDEX idx_accounts_supabase_user ON accounts(supabase_user_id);

-- Add RLS policies for Supabase Auth
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE account_chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

-- Policies for accounts
CREATE POLICY "Users can read their own account"
    ON accounts FOR SELECT
    USING (supabase_user_id = auth.uid());

-- Policies for account_chats
CREATE POLICY "Users can read their linked chats"
    ON account_chats FOR SELECT
    USING (account_id IN (
        SELECT id FROM accounts WHERE supabase_user_id = auth.uid()
    ));

-- Policies for chat_history
CREATE POLICY "Users can read their chat history"
    ON chat_history FOR SELECT
    USING (account_id IN (
        SELECT id FROM accounts WHERE supabase_user_id = auth.uid()
    ));