#!/bin/bash
# Fix RLS (Row Level Security) Issues in Supabase using the Supabase CLI
# This script enables Row Level Security on all tables in the public schema
# and sets up appropriate security policies to ensure data is properly protected.

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "Supabase CLI is not installed. Please install it first:"
    echo "npm install -g supabase"
    exit 1
fi

# Check if user is logged in
if ! supabase projects list &> /dev/null; then
    echo "You are not logged in to Supabase CLI. Please login first:"
    echo "supabase login"
    exit 1
fi

# Get the project ID
echo "Please enter your Supabase project ID (found in the project settings):"
read PROJECT_ID

# Check if project ID is provided
if [ -z "$PROJECT_ID" ]; then
    echo "Project ID is required."
    exit 1
fi

# Create a temporary SQL file
TMP_SQL_FILE=$(mktemp)

# Write SQL to the temporary file
cat > "$TMP_SQL_FILE" << 'EOF'
-- Fix RLS (Row Level Security) Issues in Supabase
-- This script enables Row Level Security on all tables in the public schema
-- and sets up appropriate security policies to ensure data is properly protected.

-- Enable RLS on temporary_accounts
ALTER TABLE public.temporary_accounts ENABLE ROW LEVEL SECURITY;
-- Create policy for temporary_accounts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy 
        WHERE schemaname = 'public' 
        AND tablename = 'temporary_accounts' 
        AND polname = 'Users can only access their own data'
    ) THEN
        CREATE POLICY "Users can only access their own data" ON public.temporary_accounts
        FOR ALL USING (auth.uid() = account_id);
    END IF;
END
$$;

-- Enable RLS on account_settings
ALTER TABLE public.account_settings ENABLE ROW LEVEL SECURITY;
-- Create policy for account_settings
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy 
        WHERE schemaname = 'public' 
        AND tablename = 'account_settings' 
        AND polname = 'Users can only access their own data'
    ) THEN
        CREATE POLICY "Users can only access their own data" ON public.account_settings
        FOR ALL USING (auth.uid() = account_id);
    END IF;
END
$$;

-- Enable RLS on migration_mapping
ALTER TABLE public.migration_mapping ENABLE ROW LEVEL SECURITY;
-- Create policy for migration_mapping
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy 
        WHERE schemaname = 'public' 
        AND tablename = 'migration_mapping' 
        AND polname = 'Enable read access for authenticated users'
    ) THEN
        CREATE POLICY "Enable read access for authenticated users" ON public.migration_mapping
        FOR SELECT USING (auth.role() = 'authenticated');
    END IF;
END
$$;

-- Enable RLS on email_templates
ALTER TABLE public.email_templates ENABLE ROW LEVEL SECURITY;
-- Create policy for email_templates
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy 
        WHERE schemaname = 'public' 
        AND tablename = 'email_templates' 
        AND polname = 'Enable read access for authenticated users'
    ) THEN
        CREATE POLICY "Enable read access for authenticated users" ON public.email_templates
        FOR SELECT USING (auth.role() = 'authenticated');
    END IF;
END
$$;

-- Enable RLS on usage_stats
ALTER TABLE public.usage_stats ENABLE ROW LEVEL SECURITY;
-- Create policy for usage_stats
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy 
        WHERE schemaname = 'public' 
        AND tablename = 'usage_stats' 
        AND polname = 'Users can only access their own usage stats'
    ) THEN
        CREATE POLICY "Users can only access their own usage stats" ON public.usage_stats
        FOR ALL USING (auth.uid() = account_id);
    END IF;
END
$$;

-- Enable RLS on bot_rules
ALTER TABLE public.bot_rules ENABLE ROW LEVEL SECURITY;
-- Create policy for bot_rules
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy 
        WHERE schemaname = 'public' 
        AND tablename = 'bot_rules' 
        AND polname = 'Users can only access their own rules'
    ) THEN
        CREATE POLICY "Users can only access their own rules" ON public.bot_rules
        FOR ALL USING (auth.uid() = account_id);
    END IF;
END
$$;

-- Enable RLS on history_context
ALTER TABLE public.history_context ENABLE ROW LEVEL SECURITY;
-- Create policy for history_context
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy 
        WHERE schemaname = 'public' 
        AND tablename = 'history_context' 
        AND polname = 'Users can only access their own history'
    ) THEN
        CREATE POLICY "Users can only access their own history" ON public.history_context
        FOR ALL USING (auth.uid() = account_id);
    END IF;
END
$$;

-- Enable RLS on ai_model_settings
ALTER TABLE public.ai_model_settings ENABLE ROW LEVEL SECURITY;
-- Create policy for ai_model_settings
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policy 
        WHERE schemaname = 'public' 
        AND tablename = 'ai_model_settings' 
        AND polname = 'Users can only access their own settings'
    ) THEN
        CREATE POLICY "Users can only access their own settings" ON public.ai_model_settings
        FOR ALL USING (auth.uid() = account_id);
    END IF;
END
$$;

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
EOF

# Execute the SQL using Supabase CLI
echo "Executing SQL to fix RLS issues..."
supabase db execute --project-ref "$PROJECT_ID" --file "$TMP_SQL_FILE"

# Clean up
rm "$TMP_SQL_FILE"

echo "RLS fix process completed. Please check the Supabase dashboard to verify that RLS is enabled for all tables." 