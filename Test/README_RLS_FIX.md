# Supabase RLS Fix

This document explains how to fix the Row Level Security (RLS) issues in your Supabase database.

## What is RLS?

Row Level Security (RLS) is a security feature in PostgreSQL that Supabase uses to control access to rows in a table. It allows you to define policies that determine which rows a user can see or modify.

Without RLS enabled, any authenticated user could potentially access all data in your tables, which is a security concern.

## The Issue

The following tables in your database have RLS disabled:

1. public.temporary_accounts
2. public.account_settings
3. public.migration_mapping
4. public.email_templates
5. public.usage_stats
6. public.bot_rules
7. public.history_context
8. public.ai_model_settings

## The Solution

The `fix_rls.sql` script in the Test directory will:

1. Enable RLS on all the affected tables
2. Create appropriate security policies for each table
3. Check the current RLS status after the fixes

## How to Run the Script

1. Log in to your Supabase dashboard at https://app.supabase.com
2. Select your project
3. Go to the SQL Editor (in the left sidebar)
4. Create a new query
5. Copy and paste the contents of the `fix_rls.sql` file into the query editor
6. Click "Run" to execute the script

The script will:
- Enable RLS on all the affected tables
- Create appropriate security policies for each table
- Show you the current RLS status of all tables
- Show you all the policies that have been created

## Security Policies Created

The script creates the following security policies:

- For account-related tables (temporary_accounts, account_settings):
  - "Users can only access their own data" - Users can only see and modify rows where account_id matches their user ID

- For bot_rules:
  - "Users can only access their own rules" - Users can only see and modify rules where account_id matches their user ID

- For history_context:
  - "Users can only access their own history" - Users can only see and modify history where account_id matches their user ID

- For ai_model_settings:
  - "Users can only access their own settings" - Users can only see and modify settings where account_id matches their user ID

- For usage_stats:
  - "Users can only access their own usage stats" - Users can only see and modify usage stats where account_id matches their user ID

- For other tables:
  - "Enable read access for authenticated users" - Authenticated users can read all rows, but not modify them

## Troubleshooting

If you encounter any issues running the script:

1. Make sure you have the necessary permissions to modify the database schema
2. Check for any error messages in the SQL Editor
3. If a specific table doesn't exist, you can comment out that section of the script

The script is designed to be idempotent, meaning it's safe to run multiple times. It will only create policies if they don't already exist.

## After Running the Script

After running the script, refresh the Supabase dashboard and check the "Database" section. The RLS errors should no longer appear in the dashboard.

## Why We're Using SQL Instead of Python

We initially tried to use a Python script to fix the RLS issues, but it required the `exec_sql` RPC function, which isn't available by default in Supabase. Using the SQL Editor directly is more reliable and doesn't require any additional setup. 