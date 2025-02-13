import json
from datetime import datetime
import asyncio
from config.settings import (
    WHOLE_HISTORY_FILE,
    HISTORY_CONTEXT_FILE
)
from openai import OpenAI
from config.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

async def analyze_whole_history():
    """Analyze entire conversation history and update history context"""
    try:
        # Load whole history
        with open(WHOLE_HISTORY_FILE, 'r') as f:
            whole_history = json.load(f)
        
        if not whole_history:
            return
        
        # Prepare conversation history for analysis
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in whole_history 
            if 'content' in msg
        ])
        
        # Get GPT-4 to analyze the entire history
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": """Analyze the entire conversation history and create a comprehensive summary. 
                    Focus on:
                    1. Key recurring topics
                    2. Who are group of people you are talking to
                    3. People names, life facts, relations between each other, etc.
                    4. Important facts or preferences mentioned
                    5. Significant decisions or conclusions
                    6. User's behavioral patterns or preferences
                    Format the output as a structured list of important points."""
                },
                {"role": "user", "content": history_text}
            ]
        )
        
        global_summary = response.choices[0].message.content
        
        # Update history context with new global summary
        with open(HISTORY_CONTEXT_FILE, 'w') as f:
            json.dump([{
                "summary": global_summary,
                "timestamp": datetime.now().isoformat(),
                "type": "global_summary",
                "message_count": len(whole_history)
            }], f, indent=4)
            
    except Exception as e:
        print(f"Error analyzing whole history: {e}")

async def periodic_history_analysis():
    """Run whole history analysis periodically"""
    while True:
        await analyze_whole_history()
        # Wait for 24 hours before next analysis
        await asyncio.sleep(24 * 3600) 