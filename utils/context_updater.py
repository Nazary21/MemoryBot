import asyncio
import json
from datetime import datetime
from config.settings import (
    MID_TERM_FILE,
    HISTORY_CONTEXT_FILE,
    MID_TERM_MESSAGE_LIMIT
)
from openai import OpenAI
from config.settings import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

async def generate_context_summary(messages):
    """Generate a summary of key facts from messages using GPT-4"""
    prompt = """Analyze these conversation messages and extract key facts and context. 
    Focus on important information that might be relevant for future conversations.
    Format the output as a list of concise facts."""
    
    messages_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": messages_text}
        ]
    )
    
    return response.choices[0].message.content

async def update_history_context():
    """Periodically analyze mid-term memory and update history context"""
    while True:
        try:
            # Load mid-term memory
            with open(MID_TERM_FILE, 'r') as f:
                mid_term = json.load(f)
            
            if len(mid_term) >= MID_TERM_MESSAGE_LIMIT:
                # Generate summary
                summary = await generate_context_summary(mid_term)
                
                # Load and update history context
                with open(HISTORY_CONTEXT_FILE, 'r') as f:
                    history_context = json.load(f)
                
                history_context.append({
                    "summary": summary,
                    "timestamp": datetime.now().isoformat(),
                    "message_count": len(mid_term)
                })
                
                # Save updated history context
                with open(HISTORY_CONTEXT_FILE, 'w') as f:
                    json.dump(history_context, f, indent=4)
                
                # Clear mid-term memory
                with open(MID_TERM_FILE, 'w') as f:
                    json.dump([], f)
        
        except Exception as e:
            print(f"Error updating history context: {e}")
        
        # Wait for 6 hours before next update
        await asyncio.sleep(6 * 3600) 