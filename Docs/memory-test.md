# Memory, Rules and Context Management Documentation

## Directory Structure

```
memory/
├── account_{id}/              # Account-specific directory
│   ├── ai_settings.json      # AI model settings
│   ├── bot_rules.json        # Bot personality and behavior rules
│   ├── chat_history.json     # Complete chat history
│   ├── history_context.json  # Analyzed conversation context
│   ├── mid_term.json        # Extended conversation memory (last 200 messages)
│   ├── short_term.json      # Recent conversation memory (last 50 messages)
│   └── whole_history.json   # Complete conversation archive
└── *.json.migrated          # Backup of migrated legacy files
```

## Memory Management

### Memory Types

1. **Short-term Memory** (`short_term.json`)
   - Stores last 50 messages
   - Used for immediate conversation context
   - Location: `memory/account_{id}/short_term.json`
   - Structure:
     ```json
     [
       {
         "timestamp": "ISO-8601 datetime",
         "role": "user|assistant|system",
         "content": "message text"
       }
     ]
     ```

2. **Mid-term Memory** (`mid_term.json`)
   - Stores last 200 messages
   - Used for extended conversation context
   - Triggered when short-term memory exceeds 50 messages
   - Location: `memory/account_{id}/mid_term.json`
   - Same structure as short-term memory

3. **Whole History** (`whole_history.json`)
   - Complete conversation archive
   - No message limit
   - Location: `memory/account_{id}/whole_history.json`
   - Same structure as short-term memory

4. **History Context** (`history_context.json`)
   - Analyzed conversation summaries
   - Generated when short-term memory reaches 50 messages
   - Location: `memory/account_{id}/history_context.json`
   - Structure:
     ```json
     [
       {
         "timestamp": "ISO-8601 datetime",
         "category": "general|system|...",
         "summary": "context summary text"
       }
     ]
     ```

### Memory Operations

1. **Adding Messages**
   - Primary: Database storage via Supabase
   - Fallback: File-based storage in account directory
   - Process:
     1. Store in `whole_history.json`
     2. Add to `short_term.json`
     3. If short-term exceeds 50 messages:
        - Generate context summary
        - Move to `mid_term.json`

2. **Retrieving Memory**
   - Priority order:
     1. Try database
     2. Check account-specific files
     3. Return empty list if both fail
   - Auto-migration from files to database when possible

3. **Context Generation**
   - Triggered when short-term memory reaches 50 messages
   - Analyzes conversation patterns
   - Stores summaries in `history_context.json`

## Rule Management

### Rule Storage

1. **Location**: `memory/account_{id}/bot_rules.json`
2. **Structure**:
   ```json
   [
     {
       "account_id": 1,
       "rule_text": "rule content",
       "priority": 0,
       "is_active": true,
       "category": "General|Language|Personalization|Memory|Tone",
       "created_at": "ISO-8601 datetime"
     }
   ]
   ```

### Rule Operations

1. **Adding Rules**
   - Via Dashboard: POST to `/dashboard/add_rule`
   - Storage priority:
     1. Database (if available)
     2. Account-specific file storage

2. **Retrieving Rules**
   - Process:
     1. Try database query
     2. Fallback to account-specific file
     3. Create default rules if none exist

3. **Updating Rules**
   - Via Dashboard: POST to `/dashboard/update_rule`
   - Updates both database and file storage
   - Maintains rule priority and categories

4. **Deleting Rules**
   - Via Dashboard: POST to `/dashboard/remove_rule`
   - Removes from both storage systems
   - Preserves rule indices for remaining rules

## AI Settings Management

### Storage

1. **Location**: `memory/account_{id}/ai_settings.json`
2. **Structure**:
   ```json
   {
     "model": "gpt-3.5-turbo",
     "temperature": 1.0,
     "max_tokens": 2000
   }
   ```

### Operations

1. **Retrieving Settings**
   - Priority:
     1. Database query
     2. Account-specific file
     3. Default settings

2. **Updating Settings**
   - Via Dashboard: POST to `/dashboard/update_model_settings`
   - Updates both storage systems
   - Validates temperature (0-2) and max_tokens (100-3000)

## Fallback Mode

### Activation
- Triggered when database connection fails
- Uses file-based storage exclusively
- Creates account-specific directories on demand

### Migration
1. **Legacy to Account-Specific**
   - Moves files from root to account directories
   - Renames old files with `.migrated` extension
   - Preserves data integrity during transition

2. **File to Database**
   - Attempts migration when database becomes available
   - Maintains file backups after successful migration

## Dashboard Integration

### Memory Management
- Displays message counts and context entries
- Allows viewing recent messages
- Provides memory cleanup options

### Rule Management
- CRUD operations for bot rules
- Category-based organization
- Priority management
- Active/inactive status toggle

### AI Settings
- Model selection
- Temperature and token limit configuration
- Provider selection (OpenAI/Grok)

## Best Practices

1. **Memory Management**
   - Regular cleanup of old messages
   - Context generation for long conversations
   - Backup before major operations

2. **Rule Management**
   - Use categories for organization
   - Set appropriate priorities
   - Test after significant changes

3. **Error Handling**
   - Graceful fallback to file storage
   - Preserve data during migrations
   - Log all operations for debugging
