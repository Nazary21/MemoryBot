# Bot Commands Documentation

## Basic Commands

### `/start`
- **Description**: Initializes the bot and creates a temporary account
- **Usage**: `/start`
- **Response**: Welcome message with instructions for registration
- **Notes**: Creates account ID 1 in fallback mode

### `/help`
- **Description**: Shows all available commands and their brief descriptions
- **Usage**: `/help`
- **Response**: List of all available commands with descriptions

### `/register`
- **Description**: Creates a permanent account with additional features
- **Usage**: `/register`
- **Response**: Instructions for creating a permanent account

### `/status`
- **Description**: Checks your account status
- **Usage**: `/status`
- **Response**: Current account status and type (temporary/permanent)

### `/account_id`
- **Description**: Shows your current account ID
- **Usage**: `/account_id`
- **Response**: Displays your account ID and indicates if in fallback mode

## Memory Management Commands

### `/clear`
- **Description**: Clears conversation history
- **Usage**: `/clear`
- **Response**: Confirmation of history clearance
- **Effect**: Removes all messages from short-term memory

### `/session`
- **Description**: Sets the session duration
- **Usage**: `/session [duration]`
- **Parameters**: 
  - `duration`: short (3h), medium (6h), or long (12h)
- **Default**: medium (6 hours)
- **Response**: Confirmation of session duration change

### `/analyze`
- **Description**: Analyzes conversation history
- **Usage**: `/analyze`
- **Response**: Confirmation of analysis completion
- **Effect**: Updates the context based on conversation analysis

### `/context`
- **Description**: Shows recent conversation context
- **Usage**: `/context`
- **Response**: Displays recent context summary
- **Notes**: Shows most recent context entries

### `/midterm`
- **Description**: Shows mid-term memory statistics
- **Usage**: `/midterm`
- **Response**: Statistics about mid-term memory:
  - Total messages
  - User messages
  - Assistant messages
  - Time range

### `/shortterm`
- **Description**: Shows short-term memory statistics
- **Usage**: `/shortterm`
- **Response**: Statistics about short-term memory:
  - Total messages
  - User messages
  - Assistant messages
  - Time range

### `/wholehistory`
- **Description**: Shows complete history statistics
- **Usage**: `/wholehistory`
- **Response**: Statistics about entire conversation history:
  - Total messages
  - User messages
  - Assistant messages
  - Time range

### `/historycontext`
- **Description**: Shows or generates full history context
- **Usage**: `/historycontext`
- **Response**: 
  - If context exists: Displays formatted history context
  - If no context: Generates new context and displays it
- **Notes**: 
  - Automatically splits long responses
  - Includes timestamp of last update
  - Shows structured analysis of conversation patterns

## Configuration Commands

### `/rules`
- **Description**: Shows current bot rules
- **Usage**: `/rules`
- **Response**: List of active rules categorized by type:
  - Language
  - Personalization
  - Memory
  - Tone
  - General

### `/model`
- **Description**: Shows current AI model information
- **Usage**: `/model`
- **Response**: Displays current AI provider and model configuration

## Notes

1. **Fallback Mode**
   - In fallback mode, all operations use account ID 1
   - Memory operations fall back to file storage
   - Command responses indicate when in fallback mode

2. **Memory Types**
   - Short-term: Last 50 messages
   - Mid-term: Last 200 messages
   - Whole history: Complete conversation archive

3. **Context Generation**
   - Automatic when short-term memory reaches 50 messages
   - Manual through `/analyze` command
   - Updates history context file

4. **Session Management**
   - Default session: 6 hours
   - Can be changed using `/session` command
   - Sessions persist until timeout or `/clear` command
