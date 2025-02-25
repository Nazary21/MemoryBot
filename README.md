# AI Telegram Bot with Memory and Multi-Provider Support

A Telegram bot powered by multiple AI providers (OpenAI GPT-3.5 and Grok) with conversation memory capabilities and a web dashboard for configuration.

## Features

- Natural language conversation using multiple AI providers:
  - OpenAI GPT-3.5
  - Grok
- Multi-level memory system:
  - Short-term memory (recent messages)
  - Mid-term memory (extended history, last 200 messages)
  - Full conversation history
  - Historical context analysis
- Web dashboard for:
  - AI provider configuration and switching
  - Bot status monitoring
  - Rule management
  - Memory statistics
- Group chat support with mention-based responses
- Customizable session durations
- Command system for memory and context management

## Setup

1. Clone the repository
```bash
git clone <your-repo-url>
cd <repo-name>
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
```
Edit `.env` file and add your:
- Telegram Bot Token (from @BotFather)
- OpenAI API Key
- Grok API Key (optional)

5. Initialize memory files
```bash
mkdir -p memory config
touch memory/short_term.json memory/mid_term.json memory/whole_history.json memory/history_context.json memory/rules.json config/ai_config.json
```

## Available Commands

- `/start` - Start the bot
- `/help` - Show available commands
- `/clear` - Clear conversation history
- `/session` - Set session duration (short: 3h, medium: 6h, long: 12h)
- `/analyze` - Analyze conversation history
- `/context` - Show historical context
- `/midterm` - Show mid-term memory stats
- `/shortterm` - Show short-term memory stats
- `/wholehistory` - Show whole history stats
- `/historycontext` - Show full history context
- `/rules` - Show current bot rules
- `/model` - Show current AI model

## Web Dashboard

The bot includes a web interface accessible at `/dashboard` with features for:
- Monitoring bot status
- Switching between AI providers
- Managing API keys
- Viewing memory statistics
- Setting and managing conversation rules
- Viewing recent messages

## Deployment

The bot is configured for deployment on Railway.app. Set the following environment variables in your Railway project:

- `TELEGRAM_TOKEN`
- `OPENAI_API_KEY`
- `GROK_API_KEY` (optional)
- `PORT` (optional, defaults to 8000)
- `MOCK_MODE` (optional, defaults to false)

## Development

To run the bot locally:
```bash
uvicorn bot:app --reload
```

## Development Requirements

### Python Version
This project requires Python 3.7-3.11. Python 3.11.x is recommended for optimal compatibility.
Python 3.12 or newer is not officially supported by the Supabase Python client.

### Dependencies
Install dependencies using:
```bash
pip install -r requirements.txt
```

Key dependencies:
- Supabase 2.13.0 (Python client for Supabase)
- FastAPI 0.109.2 (Web framework)
- Python-Telegram-Bot 20.7 (Telegram bot API)
- OpenAI 1.12.0 (OpenAI API client)

## Security Notes

- Never commit your `.env` file or any files containing API keys
- Use environment variables for all sensitive data
- Regularly rotate your API keys
- Monitor your API usage
- The bot validates webhook tokens and includes error logging

## Memory System

The bot uses a sophisticated memory system:
- Short-term: Recent messages from the current session
- Mid-term: Last 200 messages for context analysis
- Whole history: Complete conversation archive
- History context: AI-generated summaries of important information

## AI Provider System

The bot supports multiple AI providers:
- Easy switching between providers via dashboard
- Provider-specific configuration
- Automatic API key management
- Fallback mechanisms if a provider is unavailable

## License

[Your License Here]
