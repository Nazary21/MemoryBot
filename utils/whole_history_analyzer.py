import json
from datetime import datetime
import asyncio
import os
import logging
from config.settings import (
    WHOLE_HISTORY_FILE,
    HISTORY_CONTEXT_FILE
)
from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

async def analyze_whole_history(memory_manager):
    """
    Analyze entire conversation history and update history context.
    Args:
        memory_manager: Instance of MemoryManager or HybridMemoryManager
    Returns:
        dict: The generated context summary if successful, None if failed
    """
    try:
        # Load whole history using memory manager
        whole_history = memory_manager._load_memory(memory_manager.whole_history_file)
        
        if not whole_history:
            logger.info("No history to analyze")
            return None
        
        # Prepare conversation history for analysis
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in whole_history 
            if 'content' in msg and msg.get('content') and msg.get('role')
        ])
        
        if not history_text.strip():
            logger.info("No valid messages found in history")
            return None

        # Get GPT-4 to analyze the entire history
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
            logger.info("Generated summary is too short or empty")
            return None
            
        context_data = {
            "summary": global_summary,
            "timestamp": datetime.now().isoformat(),
            "type": "global_summary",
            "message_count": len(whole_history)
        }
        
        # Update history context using memory manager
        memory_manager._save_memory(memory_manager.history_file, [context_data])
        logger.info(f"Updated history context for account {memory_manager.account_id}")
            
        return context_data
            
    except Exception as e:
        logger.error(f"Error analyzing whole history: {str(e)}")
        return None

async def periodic_history_analysis(memory_manager):
    """Run whole history analysis periodically"""
    while True:
        await analyze_whole_history(memory_manager)
        # Wait for 24 hours before next analysis
        await asyncio.sleep(24 * 3600) 