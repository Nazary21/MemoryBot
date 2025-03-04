import json
from datetime import datetime
import asyncio
import os
import logging
from typing import Optional, Dict
from config.settings import (
    WHOLE_HISTORY_FILE,
    HISTORY_CONTEXT_FILE
)
from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# Constants
MIN_MESSAGES_FOR_ANALYSIS = 5  # Minimum messages needed for analysis

async def analyze_whole_history(memory_manager) -> Optional[Dict]:
    """
    Analyze entire conversation history and update history context.
    
    Args:
        memory_manager: Instance of MemoryManager or HybridMemoryManager
    Returns:
        dict: The generated context summary if successful, None if failed
    """
    try:
        # Get messages directly from file in fallback mode
        chat_id = memory_manager.account_id  # This will be the chat_id in fallback mode
        
        # Load messages from files
        short_term = memory_manager._load_memory_from_file('short_term')
        mid_term = memory_manager._load_memory_from_file('mid_term')
        whole_history = memory_manager._load_memory_from_file('whole_history')
        
        # Combine all messages
        all_messages = short_term + mid_term + whole_history
        
        # Remove duplicates based on content and timestamp
        seen = set()
        valid_messages = []
        for msg in all_messages:
            msg_id = f"{msg.get('timestamp')}_{msg.get('content')}"
            if msg_id not in seen and msg.get('content') and msg.get('role'):
                seen.add(msg_id)
                valid_messages.append(msg)
        
        # Sort by timestamp
        valid_messages.sort(key=lambda x: x.get('timestamp', ''))
        
        if len(valid_messages) < MIN_MESSAGES_FOR_ANALYSIS:
            logger.info(f"Not enough valid messages for analysis. Found {len(valid_messages)}, need at least {MIN_MESSAGES_FOR_ANALYSIS}")
            return None
        
        # Prepare conversation history for analysis (last 100 messages)
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in valid_messages[-100:]
        ])

        # Get GPT-4 to analyze the history
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": """Analyze the conversation history and create a concise summary.
                    Focus on key information that would be valuable for future conversations."""
                },
                {"role": "user", "content": history_text}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        global_summary = response.choices[0].message.content
        
        if not global_summary or len(global_summary.strip()) < 50:
            logger.warning("Generated summary is too short or empty")
            return None
            
        context_data = {
            "summary": global_summary,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(valid_messages)
        }
        
        # Save context
        history_file = os.path.join(memory_manager.memory_dir, f"account_{chat_id}", HISTORY_CONTEXT_FILE)
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump(context_data, f, indent=2)
            
        logger.info(f"Updated history context with {len(valid_messages)} messages")
        return context_data
            
    except Exception as e:
        logger.error(f"Error analyzing whole history: {str(e)}", exc_info=True)
        return None

async def periodic_history_analysis(memory_manager):
    """Run whole history analysis periodically"""
    while True:
        await analyze_whole_history(memory_manager)
        # Wait for 24 hours before next analysis
        await asyncio.sleep(24 * 3600) 