import openai
import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from config.ai_providers import AIProviderManager
from openai import OpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

class AIResponseHandler:
    def __init__(self, db):
        self.provider_manager = AIProviderManager()
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.db = db
        self.default_model = "gpt-3.5-turbo"
        self.default_settings = {
            "temperature": 0.7,
            "max_tokens": 2000
        }

    async def get_account_model_settings(self, account_id: int) -> Dict:
        """Get AI model settings for an account"""
        try:
            result = await self.db.supabase.table('ai_model_settings').select(
                '*'
            ).eq('account_id', account_id).single().execute()
            
            if result.data:
                return {
                    "model": result.data['model_name'],
                    "temperature": result.data['temperature'],
                    "max_tokens": result.data['max_tokens']
                }
            return {
                "model": self.default_model,
                **self.default_settings
            }
        except Exception as e:
            logger.error(f"Error getting model settings: {e}")
            return {
                "model": self.default_model,
                **self.default_settings
            }

    async def update_model_settings(self, account_id: int, settings: Dict) -> bool:
        """Update AI model settings for an account"""
        try:
            await self.db.supabase.table('ai_model_settings').upsert({
                'account_id': account_id,
                'model_name': settings.get('model', self.default_model),
                'temperature': settings.get('temperature', self.default_settings['temperature']),
                'max_tokens': settings.get('max_tokens', self.default_settings['max_tokens'])
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating model settings: {e}")
            return False

    async def get_chat_response(self, account_id: int, messages: List[Dict]) -> Optional[str]:
        """Get chat response using account-specific settings"""
        try:
            settings = await self.get_account_model_settings(account_id)
            
            response = await self.client.chat.completions.create(
                model=settings['model'],
                messages=messages,
                temperature=settings['temperature'],
                max_tokens=settings['max_tokens']
            )
            
            # Track token usage
            total_tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0
            await self.db.track_usage(account_id, total_tokens)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error getting chat response: {e}")
            return None

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