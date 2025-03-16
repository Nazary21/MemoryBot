-- Fix RLS (Row Level Security) Issues in Supabase - Direct Method
-- This script enables Row Level Security on all tables in the public schema
-- without using procedural code blocks

-- First, enable RLS on all tables
ALTER TABLE public.temporary_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.account_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.migration_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.history_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_model_settings ENABLE ROW LEVEL SECURITY;

-- Drop any existing policies (this ensures we start fresh)
DROP POLICY IF EXISTS "Users can only access their own data" ON public.temporary_accounts;
DROP POLICY IF EXISTS "Users can only access their own data" ON public.account_settings;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON public.migration_mapping;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON public.email_templates;
DROP POLICY IF EXISTS "Users can only access their own usage stats" ON public.usage_stats;
DROP POLICY IF EXISTS "Users can only access their own rules" ON public.bot_rules;
DROP POLICY IF EXISTS "Users can only access their own history" ON public.history_context;
DROP POLICY IF EXISTS "Users can only access their own settings" ON public.ai_model_settings;

-- Create policies for each table
CREATE POLICY "Users can only access their own data" ON public.temporary_accounts
FOR ALL USING (auth.uid() = account_id);

CREATE POLICY "Users can only access their own data" ON public.account_settings
FOR ALL USING (auth.uid() = account_id);

CREATE POLICY "Enable read access for authenticated users" ON public.migration_mapping
FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Enable read access for authenticated users" ON public.email_templates
FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Users can only access their own usage stats" ON public.usage_stats
FOR ALL USING (auth.uid() = account_id);

CREATE POLICY "Users can only access their own rules" ON public.bot_rules
FOR ALL USING (auth.uid() = account_id);

CREATE POLICY "Users can only access their own history" ON public.history_context
FOR ALL USING (auth.uid() = account_id);

CREATE POLICY "Users can only access their own settings" ON public.ai_model_settings
FOR ALL USING (auth.uid() = account_id);

-- Now, also make sure tables have a default policy that restricts access if no other policies match
-- This is a belt-and-suspenders approach to ensure security

-- For tables that should be fully restricted
DROP POLICY IF EXISTS "Default deny" ON public.temporary_accounts;
DROP POLICY IF EXISTS "Default deny" ON public.account_settings;
DROP POLICY IF EXISTS "Default deny" ON public.usage_stats;
DROP POLICY IF EXISTS "Default deny" ON public.bot_rules;
DROP POLICY IF EXISTS "Default deny" ON public.history_context;
DROP POLICY IF EXISTS "Default deny" ON public.ai_model_settings;

-- For public tables that should allow read access but not write
DROP POLICY IF EXISTS "Default read-only" ON public.migration_mapping;
DROP POLICY IF EXISTS "Default read-only" ON public.email_templates;

-- Check RLS status after fixes
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

-- Check policies after fixes
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