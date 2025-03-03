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
    Ensures whole history is up to date before analysis.
    
    Args:
        memory_manager: Instance of MemoryManager or HybridMemoryManager
    Returns:
        dict: The generated context summary if successful, None if failed
    """
    try:
        # First, get latest messages from short-term and mid-term memory
        short_term = await memory_manager.get_memory(memory_manager.account_id, 'short_term')
        mid_term = await memory_manager.get_memory(memory_manager.account_id, 'mid_term')
        whole_history = await memory_manager.get_memory(memory_manager.account_id, 'whole_history')
        
        # Create a set of message IDs to avoid duplicates
        existing_ids = {msg.get('id', f"{msg.get('timestamp')}_{msg.get('content')[:50]}") for msg in whole_history}
        
        # Add any new messages from short-term and mid-term to whole history
        for msg in short_term + mid_term:
            msg_id = msg.get('id', f"{msg.get('timestamp')}_{msg.get('content')[:50]}")
            if msg_id not in existing_ids:
                whole_history.append(msg)
                existing_ids.add(msg_id)
        
        # Sort whole history by timestamp
        whole_history.sort(key=lambda x: x.get('timestamp', ''))
        
        # Update whole history in storage
        await memory_manager.db.store_chat_message(
            account_id=memory_manager.account_id,
            chat_id=memory_manager.account_id,  # Using account_id as chat_id in this case
            role="system",
            content="History synchronized",
            memory_type='whole_history'
        )
        
        if not whole_history:
            logger.info("No history found in storage")
            return None
            
        # Check if we have enough messages to analyze
        if len(whole_history) < MIN_MESSAGES_FOR_ANALYSIS:
            logger.info(f"Not enough messages for analysis. Found {len(whole_history)}, need at least {MIN_MESSAGES_FOR_ANALYSIS}")
            return None
        
        # Filter out empty or invalid messages
        valid_messages = [
            msg for msg in whole_history 
            if msg.get('content') and msg.get('role') and msg['content'].strip()
        ]
        
        if len(valid_messages) < MIN_MESSAGES_FOR_ANALYSIS:
            logger.info(f"Not enough valid messages for analysis. Found {len(valid_messages)} valid messages")
            return None
        
        # Prepare conversation history for analysis
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in valid_messages[-100:]  # Only analyze last 100 messages for context
        ])

        # Get GPT-4 to analyze the history
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": """Analyze the conversation history and create a comprehensive but concise summary.
                    Focus on key information that would be valuable for future conversations:

                    1. Key Topics & Interests:
                       - Main discussion topics
                       - Recurring themes
                       - Areas of interest

                    2. Personal Information:
                       - Names mentioned
                       - Relationships between people
                       - Important life events or facts
                       - Professional/educational background

                    3. Preferences & Patterns:
                       - Communication style
                       - Likes and dislikes
                       - Decision-making patterns
                       - Common requests or needs

                    4. Important Context:
                       - Ongoing projects or tasks
                       - Future plans mentioned
                       - Critical decisions made
                       - Unresolved matters

                    Format the output as a clear, structured list with categories.
                    Keep it factual and objective.
                    Include only information that has high confidence and relevance."""
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
            "type": "global_summary",
            "message_count": len(valid_messages),
            "total_messages": len(whole_history),
            "analyzed_messages": min(100, len(valid_messages))  # Number of messages actually analyzed
        }
        
        # Save using the memory manager's own method
        history_file = os.path.join(memory_manager.memory_dir, f"account_{memory_manager.account_id}", HISTORY_CONTEXT_FILE)
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump([context_data], f, indent=2)
            
        logger.info(f"Updated history context for account {memory_manager.account_id} with {len(valid_messages)} messages (analyzed last {min(100, len(valid_messages))})")
            
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