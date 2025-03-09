I'll help you find the main code responsible for the reply logic in your PykhBrain project. Let me search for the relevant files:

Search files...
Let me also check the AI response handler code:

Read file: utils/ai_response.py

Read file: utils/ai_response.py
Let me also check the hybrid memory manager to understand how conversation history is managed:

Read file: utils/hybrid_memory_manager.py
Based on my analysis of the codebase, here's a summary of the main code responsible for the reply logic in your PykhBrain project:

## Main Reply Logic Components

1. **Message Handler (bot.py)**
   - The core function `message_handler` in `bot.py` (lines 455-611) handles all incoming messages
   - It processes user messages, retrieves context, and generates AI responses
   - The handler follows these steps:
     1. Gets or creates an account for the chat
     2. Retrieves rules for the account
     3. Checks if the message is a reply to the bot or mentions the bot
     4. Cleans the message text
     5. Gets the memory manager for conversation history
     6. Retrieves short-term memory and history context
     7. Formats rules and prepares the system message
     8. Sends the context and user message to the AI provider
     9. Stores the response in memory
     10. Sends the response back to the user

2. **Rule Manager (utils/rule_manager.py)**
   - Manages the rules that define the bot's behavior
   - Provides methods to:
     - Get rules for an account (`get_rules`)
     - Create default rules (`create_default_rules`)
     - Format rules for the AI context (`get_formatted_rules`)
     - Add, update, and delete rules
   - Has fallback mechanisms for file-based storage when the database is unavailable

3. **AI Response Handler (utils/ai_response.py)**
   - Handles communication with AI providers (OpenAI, Grok)
   - Manages model settings (temperature, max tokens)
   - Provides methods to:
     - Get chat responses (`get_chat_response`)
     - Update model settings (`update_model_settings`)
     - Track token usage
   - Has fallback mechanisms for different API providers

4. **Hybrid Memory Manager (utils/hybrid_memory_manager.py)**
   - Manages conversation history with both database and file-based storage
   - Supports different memory types:
     - Short-term memory (recent messages)
     - Mid-term memory (extended context)
     - Whole history (complete archive)
   - Provides methods to:
     - Retrieve memory (`get_memory`)
     - Add messages (`add_message`)
     - Get history context (`get_history_context`)
   - Has fallback mechanisms for when the database is unavailable

## Key Structures and Patterns

1. **System Message Structure**
   ```
   Follow these rules strictly they define your core identity and behavior:
   [formatted rules]

   Previous conversation history context:
   [history context]
   ```

2. **Default Rules**
   - "Respond in the same language as the user's message."
   - "If you learn someone's name, use it in future responses."
   - "Keep track of important information shared in conversation."

3. **Fallback Mechanisms**
   - Every component has fallback mechanisms for when the primary method fails
   - Database operations fall back to file-based storage
   - AI provider calls have multiple fallback options

4. **Memory Types**
   - Short-term: Recent messages (last 50)
   - Mid-term: Extended conversation context (last 200)
   - Whole history: Complete conversation archive
   - History context: Summarized important information

This architecture provides a robust system for handling user messages, maintaining conversation context, and generating appropriate responses based on defined rules and conversation history.
