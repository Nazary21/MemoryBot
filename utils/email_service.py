import logging
from config.database import init_supabase
from typing import Dict

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.supabase = init_supabase()
        
    async def send_magic_link(self, email: str, metadata: Dict = None) -> bool:
        """Send magic link email using Supabase Auth"""
        try:
            await self.supabase.auth.sign_in_with_otp({
                "email": email,
                "options": {
                    "data": metadata
                }
            })
            return True
        except Exception as e:
            logger.error(f"Error sending magic link: {e}")
            return False

    async def send_welcome_email(self, email: str, account_name: str) -> bool:
        """Send welcome email using Supabase Auth"""
        try:
            # Use Supabase's email template system
            await self.supabase.rpc('send_welcome_email', {
                'p_email': email,
                'p_account_name': account_name
            })
            return True
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return False 