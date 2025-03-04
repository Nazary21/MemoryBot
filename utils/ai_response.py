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
    def __init__(self, db):
        self.provider_manager = AIProviderManager()
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.db = db
        self.default_model = "gpt-3.5-turbo"
        self.default_settings = {
            "temperature": 1.0,
            "max_tokens": 3000
        }

    async def get_account_model_settings(self, account_id: int) -> Dict:
        """Get AI model settings for an account"""
        try:
            if self.db.supabase is None:
                # Use file-based storage
                return self._get_settings_from_file(account_id)
                
            result = await self.db.supabase.from_('ai_model_settings').select(
                '*'
            ).eq('account_id', account_id).single().execute()
            
            if result.data:
                return {
                    "model": result.data['model_name'],
                    "temperature": result.data['temperature'],
                    "max_tokens": result.data['max_tokens']
                }
            return self._get_settings_from_file(account_id)
        except Exception as e:
            logger.error(f"Error getting model settings: {e}")
            return self._get_settings_from_file(account_id)

    def _get_settings_from_file(self, account_id: int) -> Dict:
        """Get settings from file storage"""
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
            return {
                "model": self.default_model,
                **self.default_settings
            }
        except Exception as e:
            logger.error(f"Error reading settings file: {e}")
            return {
                "model": self.default_model,
                **self.default_settings
            }

    async def update_model_settings(self, account_id: int, settings: Dict) -> bool:
        """Update AI model settings for an account"""
        try:
            if self.db.supabase is None:
                return self._save_settings_to_file(account_id, settings)
                
            try:
                await self.db.supabase.from_('ai_model_settings').upsert({
                    'account_id': account_id,
                    'model_name': settings.get('model', self.default_model),
                    'temperature': settings.get('temperature', self.default_settings['temperature']),
                    'max_tokens': settings.get('max_tokens', self.default_settings['max_tokens'])
                }).execute()
                return True
            except Exception as db_error:
                logger.error(f"Database error updating settings: {db_error}")
                return self._save_settings_to_file(account_id, settings)
        except Exception as e:
            logger.error(f"Error updating model settings: {e}")
            return False

    def _save_settings_to_file(self, account_id: int, settings: Dict) -> bool:
        """Save settings to file storage"""
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
        """Get chat response using account-specific settings"""
        try:
            # For backward compatibility, handle both int and list as first parameter
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
            
            # Try using the old method first in fallback mode
            if self.db.supabase is None:
                logger.info("Using fallback mode - trying old method first")
                try:
                    return await self.get_chat_response_old(messages, settings['temperature'])
                except Exception as old_method_error:
                    logger.error(f"Error with old method: {old_method_error}")
                    # Continue to try OpenAI client as last resort
            
            # Try OpenAI client
            try:
                if not OPENAI_API_KEY:
                    raise ValueError("OpenAI API key not configured")
                    
                response = await self.client.chat.completions.create(
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
                
                return response.choices[0].message.content
            except Exception as openai_error:
                logger.error(f"OpenAI API error: {openai_error}")
                
                # Try old method as fallback if not already tried
                if self.db.supabase is not None:
                    try:
                        return await self.get_chat_response_old(messages, settings['temperature'])
                    except Exception as fallback_error:
                        logger.error(f"Error with fallback method: {fallback_error}")
                
                raise  # Re-raise the error if all attempts failed
                
        except Exception as e:
            logger.error(f"Error getting chat response: {e}")
            return "I apologize, but I encountered an error. Please try again."

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo-preview"
        ]

    async def get_chat_response_old(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Get response from the currently active AI provider"""
        provider_info = self.provider_manager.get_provider()
        logger.info(f"Using AI provider: {provider_info['name']}")
        
        if not provider_info["api_key"]:
            raise ValueError(f"API key not configured for {provider_info['name']}")
            
        if provider_info["name"].lower() == "openai":
            logger.info("Using OpenAI API")
            return await self._get_openai_response(messages, temperature, provider_info["api_key"])
        elif provider_info["name"].lower() == "grok":
            logger.info("Using Grok API")
            return await self._get_grok_response(messages, temperature, provider_info)
        else:
            raise ValueError(f"Unknown provider: {provider_info['name']}")
            
    async def _get_openai_response(self, messages: List[Dict[str, str]], temperature: float, api_key: str) -> str:
        """Get response from OpenAI API"""
        client = openai.AsyncOpenAI(api_key=api_key)
        try:
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")
            
    async def _get_grok_response(self, messages: List[Dict[str, str]], temperature: float, provider_info: Dict[str, str]) -> str:
        """Get response from Grok API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{provider_info['endpoint']}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {provider_info['api_key']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": messages,
                        "temperature": temperature,
                        "model": provider_info.get("model", "grok-1")
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Grok API error: {e}")
            raise Exception(f"Grok API error: {str(e)}")

    def get_current_model(self) -> str:
        """Get current AI model information"""
        provider_info = self.provider_manager.get_provider()
        return f"{provider_info['display_name']} ({provider_info['model']})"

def get_ai_response(messages: List[Dict[str, str]], provider_config: Dict[str, Any]) -> str:
    """Get AI response using configured provider"""
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