import logging
from typing import Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes
from utils.database import Database
import secrets
import string
from utils.email_service import EmailService
from datetime import datetime, timedelta
from utils.supabase_auth import SupabaseAuth

logger = logging.getLogger(__name__)

class RegistrationHandler:
    def __init__(self, db: Database):
        self.db = db
        self.email_service = EmailService()
        self.auth = SupabaseAuth()
        self.pending_registrations = {}  # Store temporary registration tokens

    def generate_token(self, length: int = 32) -> str:
        """Generate a secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    async def handle_register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /register command"""
        try:
            chat_id = update.effective_chat.id
            
            # Check if already registered
            account = await self.db.get_account_by_chat(chat_id)
            if account:
                await update.message.reply_text(
                    "This chat is already registered with a permanent account! 🎉\n"
                    "Use /status to see your account details."
                )
                return

            # Store registration metadata
            metadata = {
                'chat_id': chat_id,
                'user_id': update.effective_user.id,
                'registration_type': 'telegram_bot'
            }

            # Send magic link using Supabase Auth
            if await self.auth.send_magic_link(
                email=update.message.text,
                metadata=metadata
            ):
                await update.message.reply_text(
                    "✉️ Check your email!\n\n"
                    "I've sent you a magic link to complete your registration.\n"
                    "Click the link in the email to set up your account."
                )
            else:
                await update.message.reply_text(
                    "Sorry, there was an error sending the registration email.\n"
                    "Please try again later."
                )

        except Exception as e:
            logger.error(f"Error in handle_register_command: {e}")
            await update.message.reply_text(
                "Sorry, there was an error processing your registration."
            )

    async def handle_email_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle email-based registration"""
        try:
            email = update.message.text.strip().lower()
            chat_id = update.effective_chat.id
            
            # Validate email
            if '@' not in email or '.' not in email:
                await update.message.reply_text("Please provide a valid email address.")
                return

            # Generate token
            token = self.generate_token()
            
            # Store pending registration
            self.pending_registrations[token] = {
                'chat_id': chat_id,
                'email': email,
                'user_id': update.effective_user.id,
                'expires_at': datetime.now() + timedelta(hours=1)
            }
            
            # Send magic link
            if await self.email_service.send_magic_link(email, token):
                await update.message.reply_text(
                    "✉️ Check your email!\n\n"
                    "I've sent you a magic link to complete registration.\n"
                    "The link will expire in 1 hour."
                )
            else:
                await update.message.reply_text(
                    "Sorry, there was an error sending the email. Please try again."
                )

        except Exception as e:
            logger.error(f"Error in handle_email_registration: {e}")
            await update.message.reply_text(
                "Sorry, there was an error processing your registration."
            )

    async def handle_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /status command"""
        try:
            chat_id = update.effective_chat.id
            
            # Get account information
            account = await self.db.get_account_by_chat(chat_id)
            
            if not account:
                temp_account = await self.db.get_or_create_temporary_account(chat_id)
                await update.message.reply_text(
                    "📝 Current Status: Temporary Account\n\n"
                    f"Created: {temp_account['created_at']}\n"
                    f"Expires: {temp_account['expires_at']}\n\n"
                    "Use /register to create a permanent account!"
                )
                return

            # Show permanent account status
            await update.message.reply_text(
                "📝 Current Status: Permanent Account\n\n"
                f"Account Name: {account['name']}\n"
                f"Created: {account['created_at']}\n"
                "Type /help to see all available commands!"
            )

        except Exception as e:
            logger.error(f"Error in handle_status_command: {e}")
            await update.message.reply_text(
                "Sorry, there was an error checking your status. Please try again later."
            ) 