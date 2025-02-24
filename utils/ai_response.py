import openai
import httpx
import json
import logging
from typing import List, Dict, Any
from config.ai_providers import AIProviderManager

logger = logging.getLogger(__name__)

class AIResponseHandler:
    def __init__(self):
        self.provider_manager = AIProviderManager()

    async def get_chat_response(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
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