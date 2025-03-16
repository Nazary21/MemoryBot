-- Check current user and permissions
SELECT current_user, current_setting('role');

-- Check if current user has necessary permissions for RLS management
SELECT
    r.rolname,
    r.rolsuper,
    r.rolinherit,
    r.rolcreaterole,
    r.rolcreatedb,
    r.rolcanlogin,
    r.rolreplication,
    r.rolbypassrls
FROM
    pg_roles r
WHERE
    r.rolname = current_user;

-- Check existing RLS configuration for tables
SELECT
    n.nspname as schema,
    c.relname as table,
    CASE WHEN c.relrowsecurity THEN 'enabled' ELSE 'disabled' END as rls,
    CASE WHEN c.relforcerowsecurity THEN 'forced' ELSE 'not forced' END as rls_forced
FROM
    pg_class c
JOIN
    pg_namespace n ON n.oid = c.relnamespace
WHERE
    n.nspname = 'public'
    AND c.relkind = 'r'
ORDER BY
    n.nspname, c.relname;

-- Check existing policies
SELECT
    schemaname,
    tablename,
    polname as policy_name,
    cmd as command,
    permissive,
    roles,
    qual as policy_condition
FROM
    pg_policy
WHERE
    schemaname = 'public'
ORDER BY
    tablename, polname;

-- Check table ownership
SELECT
    n.nspname as schema,
    c.relname as table,
    a.rolname as owner
FROM
    pg_class c
JOIN
    pg_namespace n ON n.oid = c.relnamespace
JOIN
    pg_authid a ON a.oid = c.relowner
WHERE
    n.nspname = 'public'
    AND c.relkind = 'r'
ORDER BY
    n.nspname, c.relname; 