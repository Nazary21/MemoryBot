-- Fix RLS (Row Level Security) Issues in Supabase - Individual Table Approach
-- This script enables Row Level Security on each table one by one
-- You can run sections separately if you encounter errors with specific tables

-- *** Table 1: temporary_accounts ***
-- Enable RLS
ALTER TABLE public.temporary_accounts ENABLE ROW LEVEL SECURITY;
-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can only access their own data" ON public.temporary_accounts;
-- Create policy
CREATE POLICY "Users can only access their own data" ON public.temporary_accounts
FOR ALL USING (auth.uid() = account_id);
-- Verify
SELECT 
    n.nspname as schema, 
    c.relname as table, 
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'temporary_accounts';

-- *** Table 2: account_settings ***
-- Enable RLS
ALTER TABLE public.account_settings ENABLE ROW LEVEL SECURITY;
-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can only access their own data" ON public.account_settings;
-- Create policy
CREATE POLICY "Users can only access their own data" ON public.account_settings
FOR ALL USING (auth.uid() = account_id);
-- Verify
SELECT 
    n.nspname as schema, 
    c.relname as table, 
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'account_settings';

-- *** Table 3: migration_mapping ***
-- Enable RLS
ALTER TABLE public.migration_mapping ENABLE ROW LEVEL SECURITY;
-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON public.migration_mapping;
-- Create policy
CREATE POLICY "Enable read access for authenticated users" ON public.migration_mapping
FOR SELECT USING (auth.role() = 'authenticated');
-- Verify
SELECT 
    n.nspname as schema, 
    c.relname as table, 
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'migration_mapping';

-- *** Table 4: email_templates ***
-- Enable RLS
ALTER TABLE public.email_templates ENABLE ROW LEVEL SECURITY;
-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON public.email_templates;
-- Create policy
CREATE POLICY "Enable read access for authenticated users" ON public.email_templates
FOR SELECT USING (auth.role() = 'authenticated');
-- Verify
SELECT 
    n.nspname as schema, 
    c.relname as table, 
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'email_templates';

-- *** Table 5: usage_stats ***
-- Enable RLS
ALTER TABLE public.usage_stats ENABLE ROW LEVEL SECURITY;
-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can only access their own usage stats" ON public.usage_stats;
-- Create policy
CREATE POLICY "Users can only access their own usage stats" ON public.usage_stats
FOR ALL USING (auth.uid() = account_id);
-- Verify
SELECT 
    n.nspname as schema, 
    c.relname as table, 
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'usage_stats';

-- *** Table 6: bot_rules ***
-- Enable RLS
ALTER TABLE public.bot_rules ENABLE ROW LEVEL SECURITY;
-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can only access their own rules" ON public.bot_rules;
-- Create policy
CREATE POLICY "Users can only access their own rules" ON public.bot_rules
FOR ALL USING (auth.uid() = account_id);
-- Verify
SELECT 
    n.nspname as schema, 
    c.relname as table, 
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'bot_rules';

-- *** Table 7: history_context ***
-- Enable RLS
ALTER TABLE public.history_context ENABLE ROW LEVEL SECURITY;
-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can only access their own history" ON public.history_context;
-- Create policy
CREATE POLICY "Users can only access their own history" ON public.history_context
FOR ALL USING (auth.uid() = account_id);
-- Verify
SELECT 
    n.nspname as schema, 
    c.relname as table, 
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'history_context';

-- *** Table 8: ai_model_settings ***
-- Enable RLS
ALTER TABLE public.ai_model_settings ENABLE ROW LEVEL SECURITY;
-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can only access their own settings" ON public.ai_model_settings;
-- Create policy
CREATE POLICY "Users can only access their own settings" ON public.ai_model_settings
FOR ALL USING (auth.uid() = account_id);
-- Verify
SELECT 
    n.nspname as schema, 
    c.relname as table, 
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'ai_model_settings';

-- Final verification: Check RLS status for all tables
SELECT
    n.nspname as schema,
    c.relname as table,
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls
FROM
    pg_class c
JOIN
    pg_namespace n ON n.oid = c.relnamespace
WHERE
    n.nspname = 'public'
    AND c.relkind = 'r'
ORDER BY
    n.nspname, c.relname;

-- Check all policies
SELECT
    schemaname,
    tablename,
    polname as policy_name,
    cmd as command,
    permissive
FROM
    pg_policy
WHERE
    schemaname = 'public'
ORDER BY
    tablename, polname; 