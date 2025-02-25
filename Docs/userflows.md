# User Flows and Authentication

## Authentication Flows

### 1. Temporary Account Flow (Quick Start)
1. **First Interaction**
   - User starts a chat with the bot
   - Bot automatically creates a temporary account linked to the chat ID
   - User gets immediate access to all bot functionality
   - Data is stored with the temporary account ID

2. **Temporary Account Limitations**
   - Limited to a single chat/group
   - Data persists for 30 days
   - No dashboard access
   - Basic functionality only

3. **Temporary Account Storage**
   - Stored in `temporary_accounts` table
   - Linked to Telegram chat ID
   - Automatic expiration after 30 days

### 2. Permanent Account Registration
1. **Registration Command**
   - User types `/register` in the Telegram chat
   - Bot sends instructions for registration
   - User completes registration via email verification
   - Temporary account data is migrated to permanent account

2. **Permanent Account Benefits**
   - Web dashboard access
   - Multiple chat groups
   - Persistent settings
   - Advanced features
   - No data expiration

3. **Permanent Account Storage**
   - Core data in `accounts` table
   - User authentication in `account_users` table
   - Chat associations in `account_chats` table

### 3. Dashboard Authentication
1. **Basic Authentication**
   - Currently using HTTP Basic Auth
   - Credentials stored in environment variables:
     - `DASHBOARD_USERNAME` (defaults to "admin")
     - `DASHBOARD_PASSWORD` (defaults to "pykhbrain")
   - Warning displayed when using default credentials

2. **Future Authentication Plans**
   - Supabase Auth integration for email-based login
   - Magic link authentication
   - JWT session management
   - Role-based access control

## Database Setup and Synchronization

### 1. Database Initialization
1. **Application Startup**
   - `startup_event()` function in `bot.py` triggers initialization
   - `db.setup_tables()` ensures all required tables exist
   - Default account (ID=1) is created if it doesn't exist
   - Default rules are created for new accounts

2. **Table Creation Process**
   - Tables are created if they don't exist using SQL statements
   - Schema follows the structure defined in `migrations/init.sql`
   - Fallback mechanisms handle connection issues

3. **Fallback Mechanisms**
   - File-based storage used when database connection fails
   - Automatic migration from files to database when connection is restored
   - Memory directory with JSON files serves as backup storage

### 2. Rule Management and Synchronization

1. **Rule Creation**
   - Default rules created for new accounts via `rule_manager.create_default_rules()`
   - Rules stored in `bot_rules` table with account association
   - Each rule has text, priority, and active status

2. **Rule Synchronization**
   - Rules are account-specific (tenant isolation)
   - Admin dashboard can modify rules for account ID 1
   - Changes persist in database for future sessions
   - File-based fallback ensures rules are available even without database

3. **Default Rules**
   - Created automatically for new accounts
   - Include general behavior, language, personalization, memory, and tone guidelines
   - Applied during chat interactions

## User Management

### 1. Admin User
1. **Dashboard Access**
   - Full access to dashboard via HTTP Basic Auth
   - Can modify rules, AI provider settings, and view statistics
   - Default credentials (admin/pykhbrain) if not configured

2. **Admin Capabilities**
   - Manage GPT rules
   - Configure AI providers
   - View system status
   - Monitor recent messages

### 2. Regular Users
1. **Telegram Interaction**
   - Interact with bot via Telegram
   - Automatic temporary account creation
   - Option to register for permanent account

2. **Dashboard Access (Future)**
   - Will access personalized dashboard after authentication
   - Manage their own rules and settings
   - View their chat history and statistics

## Multi-Tenant Implementation

### 1. Current Status
- Database schema set up with tenant isolation
- Supabase Auth integration complete
- Row Level Security (RLS) policies implemented
- Testing phase in progress

### 2. Data Isolation
- Each account can only access their own data
- Chat histories are tenant-isolated
- Rules are account-specific
- Settings are per-account

### 3. Migration Path
- Temporary accounts can be upgraded to permanent
- Data automatically migrates during upgrade
- Backward compatibility with file-based storage

## Testing Checklist

### 1. Basic Functionality
- [ ] Bot responds to messages
- [ ] Rules are applied to responses
- [ ] Memory persists between sessions

### 2. Authentication
- [ ] Dashboard access with correct credentials
- [ ] Dashboard rejection with incorrect credentials
- [ ] Default credentials warning when applicable

### 3. Database Operations
- [ ] Tables created on startup
- [ ] Default rules created for new accounts
- [ ] File fallback works when database unavailable
