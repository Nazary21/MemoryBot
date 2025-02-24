import os
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AIProvider:
    def __init__(self, name: str, api_key: str, endpoint: str, model: str):
        self.name = name
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "api_key": "●" * 8 + self.api_key[-4:] if self.api_key else "",  # Mask API key
            "endpoint": self.endpoint,
            "model": self.model
        }

class AIProviderManager:
    _instance = None

    def __new__(cls, config_file: str = "config/ai_config.json"):
        if cls._instance is None:
            logger.info("Creating new AIProviderManager instance")
            cls._instance = super(AIProviderManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_file: str = "config/ai_config.json"):
        if not self._initialized:
            logger.info("Initializing AIProviderManager")
            self.config_file = config_file
            self.config = {
                "active_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": os.getenv("OPENAI_API_KEY", ""),
                        "endpoint": "https://api.openai.com/v1",
                        "model": "gpt-3.5-turbo",
                        "display_name": "OpenAI (GPT-3.5)"
                    },
                    "grok": {
                        "api_key": os.getenv("GROK_API_KEY", ""),
                        "endpoint": "https://api.x.ai/v1",
                        "model": "grok-2-latest",
                        "display_name": "Grok"
                    }
                }
            }
            self._ensure_config_file()
            self._load_config()
            self._initialized = True

    def _ensure_config_file(self):
        """Ensure config file exists"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            if not os.path.exists(self.config_file):
                logger.info(f"Creating new config file at {self.config_file}")
                self._save_config()
        except Exception as e:
            logger.error(f"Error ensuring config file: {e}")

    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    stored_config = json.load(f)
                    self.config["active_provider"] = stored_config.get("active_provider", self.config["active_provider"])
                    logger.info(f"Loaded config, active provider: {self.config['active_provider']}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def _save_config(self):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump({"active_provider": self.config["active_provider"]}, f, indent=2)
            logger.info(f"Saved config with active provider: {self.config['active_provider']}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get_provider(self, name: str = None) -> Dict:
        """Get provider configuration"""
        name = name or self.config["active_provider"]
        logger.info(f"Getting provider config for: {name}")
        provider_config = self.config["providers"].get(name, self.config["providers"]["openai"])
        
        # Always use environment variables for API keys if available
        env_key = os.getenv(f"{name.upper()}_API_KEY")
        if env_key:
            provider_config["api_key"] = env_key
        
        return {
            "name": name,
            "api_key": provider_config["api_key"],
            "endpoint": provider_config["endpoint"],
            "model": provider_config["model"],
            "display_name": provider_config["display_name"]
        }

    def set_active_provider(self, provider: str) -> bool:
        """Set active AI provider"""
        if provider in self.config["providers"]:
            provider_info = self.get_provider(provider)
            if provider_info["api_key"]:
                self.config["active_provider"] = provider
                logger.info(f"Setting active provider to: {provider}")
                self._save_config()
                return True
            logger.warning(f"Cannot switch to {provider}: no API key configured")
            return False
        logger.error(f"Invalid provider: {provider}")
        return False

    def get_active_provider(self) -> str:
        """Get currently active provider"""
        return self.config["active_provider"] 