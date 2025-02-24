# AI Telegram Bot with Memory

A Telegram bot powered by OpenAI's GPT-3.5 with conversation memory capabilities.

## Features

- Natural language conversation using GPT-3.5
- Short-term and mid-term memory
- Historical context analysis
- Multiple session duration options
- Command system for memory management

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

5. Initialize memory files
```bash
mkdir -p memory
touch memory/short_term.json memory/mid_term.json memory/whole_history.json memory/history_context.json
```

## Available Commands

- `/start` - Start the bot
- `/help` - Show available commands
- `/clear` - Clear conversation history
- `/session` - Set session duration
- `/analyze` - Analyze conversation history
- `/context` - Show historical context
- `/midterm` - Show mid-term memory stats
- `/shortterm` - Show short-term memory stats
- `/wholehistory` - Show whole history stats
- `/historycontext` - Show full history context

## Deployment

The bot is configured for deployment on Railway.app. Make sure to set the following environment variables in your Railway project:

- `TELEGRAM_TOKEN`
- `OPENAI_API_KEY`
- `PORT` (optional, defaults to 8000)
- `MOCK_MODE` (optional, defaults to false)

## Development

To run the bot locally:
```bash
uvicorn bot:app --reload
```

## Security Notes

- Never commit your `.env` file or any files containing API keys
- Use environment variables for all sensitive data
- Regularly rotate your API keys
- Monitor your API usage

## License

[Your License Here]
