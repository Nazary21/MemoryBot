from typing import Optional, Dict
from config.database import init_supabase
import logging

logger = logging.getLogger(__name__)

class SupabaseAuth:
    def __init__(self):
        self.client = init_supabase()

    async def sign_up_with_email(self, email: str, password: str, metadata: Dict = None) -> Dict:
        """Sign up a new user with email"""
        try:
            result = await self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": metadata
                }
            })
            return result.user
        except Exception as e:
            logger.error(f"Error in sign_up_with_email: {e}")
            raise

    async def send_magic_link(self, email: str, metadata: Dict = None) -> bool:
        """Send magic link for passwordless auth"""
        try:
            await self.client.auth.sign_in_with_otp({
                "email": email,
                "options": {
                    "data": metadata
                }
            })
            return True
        except Exception as e:
            logger.error(f"Error sending magic link: {e}")
            return False

    async def verify_token(self, token: str) -> Optional[Dict]:
        """Verify a JWT token"""
        try:
            result = await self.client.auth.verify_otp({
                "token": token,
                "type": "magiclink"
            })
            return result.user
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            result = await self.client.auth.admin.get_user_by_id(user_id)
            return result.user
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    async def update_user_metadata(self, user_id: str, metadata: Dict) -> bool:
        """Update user metadata"""
        try:
            await self.client.auth.admin.update_user_by_id(
                user_id,
                {"user_metadata": metadata}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user metadata: {e}")
            return False 