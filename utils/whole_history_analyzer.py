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
        # Get messages from memory manager
        short_term = memory_manager._load_memory_from_file('short_term')
        mid_term = memory_manager._load_memory_from_file('mid_term')
        whole_history = memory_manager._load_memory_from_file('whole_history')
        
        logger.info(f"Loaded messages - Short term: {len(short_term)}, Mid term: {len(mid_term)}, Whole: {len(whole_history)}")
        
        # Combine all messages and remove duplicates
        all_messages = []
        seen_messages = set()
        
        for msg in short_term + mid_term + whole_history:
            # Only consider messages with required fields
            if not msg.get('content') or not msg.get('role'):
                continue
                
            # Create unique identifier
            msg_id = f"{msg.get('timestamp', '')}_{msg.get('content')}"
            
            if msg_id not in seen_messages:
                seen_messages.add(msg_id)
                all_messages.append(msg)
        
        # Sort by timestamp
        all_messages.sort(key=lambda x: x.get('timestamp', ''))
        
        # Take last 100 messages for analysis
        messages_to_analyze = all_messages[-100:]
        
        if len(messages_to_analyze) < MIN_MESSAGES_FOR_ANALYSIS:
            logger.info(f"Not enough valid messages for analysis. Found {len(messages_to_analyze)}, need at least {MIN_MESSAGES_FOR_ANALYSIS}")
            return None
            
        logger.info(f"Analyzing {len(messages_to_analyze)} messages")
        
        # Prepare conversation history
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages_to_analyze
        ])

        # Get GPT-4 to analyze the history
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": """Analyze the conversation history and create a concise summary.
                    Focus on key information that would be valuable for future conversations.
                    Include main topics discussed, user preferences, and important context."""
                },
                {"role": "user", "content": history_text}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        summary = response.choices[0].message.content.strip()
        
        if not summary or len(summary) < 50:
            logger.warning("Generated summary is too short or empty")
            return None
            
        # Save context in format compatible with get_history_context
        context_data = {
            "timestamp": datetime.now().isoformat(),
            "category": "analysis",
            "summary": summary,
            "message_count": len(messages_to_analyze),
            "total_messages": len(all_messages)
        }
        
        # Save to file
        history_file = os.path.join(memory_manager.memory_dir, f"account_{memory_manager.account_id}", HISTORY_CONTEXT_FILE)
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump(context_data, f, indent=2)
            
        logger.info(f"Successfully updated history context. Analyzed {len(messages_to_analyze)} messages out of {len(all_messages)} total")
        return context_data
            
    except Exception as e:
        logger.error(f"Error analyzing whole history: {str(e)}", exc_info=True)
        return None

async def periodic_history_analysis(memory_manager):
    """Run whole history analysis periodically"""
    while True:
        try:
            await analyze_whole_history(memory_manager)
        except Exception as e:
            logger.error(f"Error in periodic analysis: {e}")
        # Wait for 24 hours before next analysis
        await asyncio.sleep(24 * 3600) 