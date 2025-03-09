import openai
import httpx
import json
import logging
import os
from typing import List, Dict, Any, Optional
from config.ai_providers import AIProviderManager
from openai import OpenAI
from config.settings import OPENAI_API_KEY, MOCK_MODE

logger = logging.getLogger(__name__)

class AIResponseHandler:
    """
    Main class for handling AI responses with multiple providers and fallback mechanisms.
    
    This class manages:
    1. AI model settings (temperature, max_tokens)
    2. API calls to different providers (OpenAI, Grok)
    3. Fallback mechanisms when primary methods fail
    4. Storage of settings in both database and file system
    
    The design follows a robust pattern with multiple fallback paths to ensure
    the system can continue to function even when components fail.
    """
    def __init__(self, db):
        """
        Initialize the AI response handler with provider manager and default settings.
        
        Args:
            db: Database instance for storing and retrieving settings
        """
        self.provider_manager = AIProviderManager()
        self.client = OpenAI(api_key=OPENAI_API_KEY)  # Primary OpenAI client
        self.db = db
        # Default model and settings used when no custom settings are found
        self.default_model = "gpt-3.5-turbo"
        self.default_settings = {
            "temperature": 1.0,
            "max_tokens": 3000
        }

    async def get_account_model_settings(self, account_id: int) -> Dict:
        """
        Get AI model settings for a specific account.
        
        This method tries to retrieve settings from:
        1. Database (primary storage)
        2. File system (fallback storage)
        
        Args:
            account_id: The account ID to get settings for
            
        Returns:
            Dictionary with model, temperature, and max_tokens settings
        """
        try:
            # If database is unavailable, use file-based storage
            if self.db.supabase is None:
                return self._get_settings_from_file(account_id)
                
            # Try to get settings from database
            result = await self.db.supabase.from_('ai_model_settings').select(
                '*'
            ).eq('account_id', account_id).single().execute()
            
            if result.data:
                return {
                    "model": result.data['model_name'],
                    "temperature": result.data['temperature'],
                    "max_tokens": result.data['max_tokens']
                }
            # If no settings found in database, fall back to file storage
            return self._get_settings_from_file(account_id)
        except Exception as e:
            logger.error(f"Error getting model settings: {e}")
            # If any error occurs, fall back to file storage
            return self._get_settings_from_file(account_id)

    def _get_settings_from_file(self, account_id: int) -> Dict:
        """
        Get settings from file storage (fallback mechanism).
        
        This method is used when:
        1. Database is unavailable
        2. Database operations fail
        3. No settings are found in the database
        
        Args:
            account_id: The account ID to get settings for
            
        Returns:
            Dictionary with model, temperature, and max_tokens settings
        """
        try:
            settings_file = f"memory/account_{account_id}/ai_settings.json"
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    return {
                        "model": settings.get('model', self.default_model),
                        "temperature": settings.get('temperature', self.default_settings['temperature']),
                        "max_tokens": settings.get('max_tokens', self.default_settings['max_tokens'])
                    }
            # If no settings file exists, return defaults
            return {
                "model": self.default_model,
                **self.default_settings
            }
        except Exception as e:
            logger.error(f"Error reading settings file: {e}")
            # If any error occurs, return defaults
            return {
                "model": self.default_model,
                **self.default_settings
            }

    async def update_model_settings(self, account_id: int, settings: Dict) -> bool:
        """
        Update AI model settings for a specific account.
        
        This method tries to update settings in:
        1. Database (primary storage)
        2. File system (fallback storage)
        
        Args:
            account_id: The account ID to update settings for
            settings: Dictionary with model, temperature, and max_tokens settings
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            # If database is unavailable, use file-based storage
            if self.db.supabase is None:
                return self._save_settings_to_file(account_id, settings)
                
            try:
                # Try to update settings in database
                await self.db.supabase.from_('ai_model_settings').upsert({
                    'account_id': account_id,
                    'model_name': settings.get('model', self.default_model),
                    'temperature': settings.get('temperature', self.default_settings['temperature']),
                    'max_tokens': settings.get('max_tokens', self.default_settings['max_tokens'])
                }).execute()
                return True
            except Exception as db_error:
                logger.error(f"Database error updating settings: {db_error}")
                # If database operation fails, fall back to file storage
                return self._save_settings_to_file(account_id, settings)
        except Exception as e:
            logger.error(f"Error updating model settings: {e}")
            return False

    def _save_settings_to_file(self, account_id: int, settings: Dict) -> bool:
        """
        Save settings to file storage (fallback mechanism).
        
        This method is used when:
        1. Database is unavailable
        2. Database operations fail
        
        Args:
            account_id: The account ID to save settings for
            settings: Dictionary with model, temperature, and max_tokens settings
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            settings_file = f"memory/account_{account_id}/ai_settings.json"
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            
            with open(settings_file, 'w') as f:
                json.dump({
                    'model': settings.get('model', self.default_model),
                    'temperature': settings.get('temperature', self.default_settings['temperature']),
                    'max_tokens': settings.get('max_tokens', self.default_settings['max_tokens'])
                }, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving settings to file: {e}")
            return False

    async def get_chat_response(self, account_id: int, messages: List[Dict]) -> Optional[str]:
        """
        Get AI response using account-specific settings with provider flexibility.
        
        This consolidated method:
        1. Supports both account-specific settings and provider selection
        2. Works with both OpenAI and Grok providers
        3. Includes robust fallback mechanisms
        4. Tracks token usage when possible
        
        Args:
            account_id: The account ID to get settings for
            messages: List of message dictionaries with role and content
            
        Returns:
            AI response text or error message
        """
        try:
            # For backward compatibility, handle both int and list as first parameter
            # This allows the method to be called with either:
            # - get_chat_response(account_id, messages) [new signature]
            # - get_chat_response(messages, temperature) [old signature]
            if isinstance(account_id, list) and isinstance(messages, (float, int)):
                # Old method signature: get_chat_response(messages, temperature)
                temperature = messages
                messages = account_id
                account_id = 1  # Default account
                settings = {
                    "model": self.default_model,
                    "temperature": temperature,
                    "max_tokens": self.default_settings["max_tokens"]
                }
            else:
                # New method signature: get_chat_response(account_id, messages)
                try:
                    settings = await self.get_account_model_settings(account_id)
                except Exception as e:
                    logger.error(f"Error getting account settings: {e}")
                    settings = {
                        "model": self.default_model,
                        "temperature": self.default_settings["temperature"],
                        "max_tokens": self.default_settings["max_tokens"]
                    }
            
            # Get the active provider information
            provider_info = self.provider_manager.get_provider()
            provider_name = provider_info["name"].lower()
            logger.info(f"Using AI provider: {provider_name}")
            
            # Try the selected provider
            try:
                response_text = None
                
                # Use OpenAI
                if provider_name == "openai":
                    # Try using the direct OpenAI client first
                    try:
                        if not OPENAI_API_KEY and not provider_info["api_key"]:
                            raise ValueError("OpenAI API key not configured")
                        
                        # Use the client initialized in constructor with global API key
                        # or create a new client with provider-specific API key
                        client = self.client
                        if provider_info["api_key"] and provider_info["api_key"] != OPENAI_API_KEY:
                            client = OpenAI(api_key=provider_info["api_key"])
                            
                        response = await client.chat.completions.create(
                            model=settings['model'],
                            messages=messages,
                            temperature=settings['temperature'],
                            max_tokens=settings['max_tokens']
                        )
                        
                        # Track token usage if possible
                        try:
                            total_tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0
                            await self.db.track_usage(account_id, total_tokens)
                        except Exception as usage_error:
                            logger.error(f"Error tracking usage: {usage_error}")
                        
                        response_text = response.choices[0].message.content
                    except Exception as openai_error:
                        logger.error(f"OpenAI client error: {openai_error}")
                        # If direct client fails, try the AsyncOpenAI client as fallback
                        client = openai.AsyncOpenAI(api_key=provider_info["api_key"] or OPENAI_API_KEY)
                        response = await client.chat.completions.create(
                            model=settings['model'],
                            messages=messages,
                            temperature=settings['temperature']
                        )
                        response_text = response.choices[0].message.content
                
                # Use Grok
                elif provider_name == "grok":
                    if not provider_info["api_key"]:
                        raise ValueError("Grok API key not configured")
                        
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{provider_info['endpoint']}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {provider_info['api_key']}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "messages": messages,
                                "temperature": settings['temperature'],
                                "model": provider_info.get("model", "grok-1")
                            }
                        )
                        response.raise_for_status()
                        result = response.json()
                        response_text = result["choices"][0]["message"]["content"]
                
                # Unknown provider
                else:
                    raise ValueError(f"Unknown provider: {provider_name}")
                
                return response_text
                
            except Exception as provider_error:
                logger.error(f"Provider {provider_name} error: {provider_error}")
                
                # If the selected provider fails and it's not OpenAI, try OpenAI as fallback
                if provider_name != "openai" and OPENAI_API_KEY:
                    logger.info("Trying OpenAI as fallback")
                    try:
                        response = await self.client.chat.completions.create(
                            model=self.default_model,
                            messages=messages,
                            temperature=settings['temperature'],
                            max_tokens=settings['max_tokens']
                        )
                        return response.choices[0].message.content
                    except Exception as fallback_error:
                        logger.error(f"OpenAI fallback error: {fallback_error}")
                
                raise  # Re-raise the error if all attempts failed
                
        except Exception as e:
            logger.error(f"Error getting chat response: {e}")
            return "I apologize, but I encountered an error. Please try again."

    def get_available_models(self) -> List[str]:
        """
        Get list of available models for the dashboard UI.
        
        Note: This is a hardcoded list that may need updating as new models are released.
        
        Returns:
            List of model names
        """
        return [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo-preview"
        ]

    def get_current_model(self) -> str:
        """
        Get current AI model information for display.
        
        Used in the bot's /model command to show the current model.
        
        Returns:
            String with provider name and model
        """
        provider_info = self.provider_manager.get_provider()
        return f"{provider_info['display_name']} ({provider_info['model']})"

# POTENTIALLY OBSOLETE FUNCTION
# This standalone function appears to be unused in the codebase.
# It provides a simpler alternative to the AIResponseHandler class.
def get_ai_response(messages: List[Dict[str, str]], provider_config: Dict[str, Any]) -> str:
    """
    Get AI response using configured provider.
    
    This function appears to be unused in the codebase and may be obsolete.
    It provides a simpler alternative to the AIResponseHandler class.
    
    Args:
        messages: List of message dictionaries with role and content
        provider_config: Dictionary with provider configuration
        
    Returns:
        AI response text
    """
    try:
        logger.info(f"Using AI provider: {provider_config['provider']}")
        
        if provider_config['provider'] == 'openai':
            logger.info("Using OpenAI API")
            client = OpenAI(api_key=provider_config['api_key'])
            response = client.chat.completions.create(
                model=provider_config['model'],
                messages=messages,
                temperature=provider_config.get('temperature', 0.7),
                max_tokens=provider_config.get('max_tokens', 1000)
            )
            return response.choices[0].message.content

        # ... existing code for other providers ...

    except Exception as e:
        logger.error(f"AI provider error: {str(e)}")
        raise 