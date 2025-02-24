import logging
from typing import Optional, Dict, List
from config.database import init_supabase
from datetime import datetime, timedelta
from passlib.context import CryptContext

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Database:
    def __init__(self):
        self.supabase = init_supabase()
        if self.supabase is None:
            logger.error("Failed to initialize Supabase client. Database operations will not work.")
        
    async def setup_tables(self):
        """Initialize database tables"""
        try:
            if self.supabase is None:
                logger.error("Cannot set up tables: Supabase client is not initialized")
                return
                
            # Create tables using raw SQL for more control
            await self.supabase.postgrest.rpc('create_initial_schema').execute()
        except Exception as e:
            logger.error(f"Error setting up tables: {e}")
            raise

    async def get_or_create_temporary_account(self, chat_id: int) -> Dict:
        """Get or create a temporary account for a chat"""
        try:
            if self.supabase is None:
                logger.error("Cannot get or create temporary account: Supabase client is not initialized")
                return {}
                
            # Check for existing temporary account
            result = await self.supabase.table('temporary_accounts').select('*').eq('telegram_chat_id', chat_id).execute()
            
            if result.data:
                return result.data[0]
                
            # Create new temporary account
            result = await self.supabase.table('temporary_accounts').insert({
                'telegram_chat_id': chat_id,
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat()
            }).execute()
            
            return result.data[0]
            
        except Exception as e:
            logger.error(f"Error in get_or_create_temporary_account: {e}")
            raise

    async def get_account_by_chat(self, chat_id: int) -> Optional[Dict]:
        """Get permanent account by chat ID"""
        try:
            if self.supabase is None:
                logger.error("Cannot get account by chat: Supabase client is not initialized")
                return None
                
            result = await self.supabase.table('account_chats').select(
                'accounts(*)'
            ).eq('telegram_chat_id', chat_id).execute()
            
            return result.data[0]['accounts'] if result.data else None
            
        except Exception as e:
            logger.error(f"Error in get_account_by_chat: {e}")
            return None

    async def store_chat_message(self, account_id: int, chat_id: int, role: str, content: str, memory_type: str = 'short_term'):
        """Store a chat message"""
        try:
            if self.supabase is None:
                logger.error("Cannot store chat message: Supabase client is not initialized")
                return
                
            await self.supabase.table('chat_history').insert({
                'account_id': account_id,
                'telegram_chat_id': chat_id,
                'role': role,
                'content': content,
                'memory_type': memory_type
            }).execute()
        except Exception as e:
            logger.error(f"Error storing chat message: {e}")
            raise

    async def get_chat_memory(self, chat_id: int, memory_type: str = 'short_term', limit: int = 50) -> List[Dict]:
        """Get chat memory by type"""
        try:
            if self.supabase is None:
                logger.error("Cannot get chat memory: Supabase client is not initialized")
                return []
                
            result = await self.supabase.table('chat_history').select('*').eq(
                'telegram_chat_id', chat_id
            ).eq('memory_type', memory_type).order('timestamp', desc=True).limit(limit).execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting chat memory: {e}")
            return []

    async def migrate_file_data(self, chat_id: int, account_id: int):
        """Migrate data from file system to database"""
        try:
            # This will be implemented as part of the HybridMemoryManager
            pass
        except Exception as e:
            logger.error(f"Error migrating file data: {e}")
            raise 

    async def create_permanent_account(self, name: str, email: str, password: str, chat_id: int) -> Dict:
        """Create a permanent account"""
        try:
            if self.supabase is None:
                logger.error("Cannot create permanent account: Supabase client is not initialized")
                return {}
                
            # Hash the password
            hashed_password = pwd_context.hash(password)
            
            # Create account
            account_result = await self.supabase.table('accounts').insert({
                'name': name
            }).execute()
            
            if not account_result.data:
                logger.error("Failed to create account")
                return {}
                
            account = account_result.data[0]
            
            # Create user
            await self.supabase.table('account_users').insert({
                'account_id': account['id'],
                'email': email,
                'hashed_password': hashed_password
            }).execute()
            
            # Link chat
            await self.supabase.table('account_chats').insert({
                'account_id': account['id'],
                'telegram_chat_id': chat_id
            }).execute()
            
            logger.info(f"Successfully created permanent account for {email}")
            return account
            
        except Exception as e:
            logger.error(f"Error creating permanent account: {e}")
            raise

    async def migrate_temporary_account(self, chat_id: int, new_account_id: int):
        """Migrate temporary account data to permanent account"""
        try:
            if self.supabase is None:
                logger.error("Cannot migrate temporary account: Supabase client is not initialized")
                return
                
            # Use direct queries instead of pool which might not be available
            # Get temporary account
            temp_account = await self.get_or_create_temporary_account(chat_id)
            if not temp_account:
                logger.error("Cannot find temporary account to migrate")
                return
                
            # Migrate chat history with memory type preservation
            await self.supabase.table('chat_history').insert({
                'account_id': new_account_id,
                'telegram_chat_id': temp_account['telegram_chat_id'],
                'role': 'system',
                'content': 'Account migrated from temporary to permanent',
                'memory_type': 'system'
            }).execute()
            
            # Mark old account as migrated
            await self.supabase.table('migration_mapping').insert({
                'old_chat_id': chat_id,
                'new_account_id': new_account_id,
                'migration_status': 'completed'
            }).execute()
            
            # Delete temporary account
            await self.supabase.table('temporary_accounts').delete().eq('id', temp_account['id']).execute()
            
            logger.info(f"Successfully migrated temporary account {temp_account['id']} to permanent account {new_account_id}")
            
        except Exception as e:
            logger.error(f"Error migrating temporary account: {e}")
            raise

    async def get_memory_by_type(self, account_id: int, memory_type: str, limit: int = 50) -> List[Dict]:
        """Get memory by type for an account"""
        try:
            if self.supabase is None:
                logger.error("Cannot get memory by type: Supabase client is not initialized")
                return []
                
            result = await self.supabase.table('chat_history').select('*').eq(
                'account_id', account_id
            ).eq('memory_type', memory_type).order('timestamp', desc=True).limit(limit).execute()
            
            return result.data
        except Exception as e:
            logger.error(f"Error getting memory by type: {e}")
            return []

    async def store_history_context(self, account_id: int, summary: str, category: str = 'general'):
        """Store analyzed history context"""
        try:
            if self.supabase is None:
                logger.error("Cannot store history context: Supabase client is not initialized")
                return
                
            await self.supabase.table('history_context').insert({
                'account_id': account_id,
                'summary': summary,
                'category': category
            }).execute()
        except Exception as e:
            logger.error(f"Error storing history context: {e}")
            raise

    async def get_history_context(self, account_id: int, limit: int = 10) -> List[Dict]:
        """Get history context summaries"""
        try:
            if self.supabase is None:
                logger.error("Cannot get history context: Supabase client is not initialized")
                return []
                
            result = await self.supabase.table('history_context').select('*').eq(
                'account_id', account_id
            ).order('created_at', desc=True).limit(limit).execute()
            
            return result.data
        except Exception as e:
            logger.error(f"Error getting history context: {e}")
            return []

    async def cleanup_old_memory(self, account_id: int, memory_type: str, older_than: datetime):
        """Clean up old memory entries"""
        try:
            if self.supabase is None:
                logger.error("Cannot cleanup old memory: Supabase client is not initialized")
                return
                
            await self.supabase.table('chat_history').delete().eq(
                'account_id', account_id
            ).eq('memory_type', memory_type).lt('timestamp', older_than.isoformat()).execute()
        except Exception as e:
            logger.error(f"Error cleaning up old memory: {e}")
            raise

    async def get_memory_stats(self, account_id: int) -> Dict:
        """Get memory statistics for an account"""
        try:
            if self.supabase is None:
                logger.error("Cannot get memory stats: Supabase client is not initialized")
                return {}
                
            stats = {}
            for memory_type in ['short_term', 'mid_term', 'whole_history']:
                result = await self.supabase.rpc('get_memory_stats', {
                    'p_account_id': account_id,
                    'p_memory_type': memory_type
                }).execute()
                stats[memory_type] = result.data[0]
            return stats
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {}

    async def get_all_accounts(self) -> List[Dict]:
        """Get all accounts (admin only)"""
        try:
            if self.supabase is None:
                logger.error("Cannot get all accounts: Supabase client is not initialized")
                return []
                
            result = await self.supabase.table('accounts').select(
                '*',
                count='exact'
            ).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting all accounts: {e}")
            return []

    async def get_total_message_count(self) -> int:
        """Get total message count across all accounts (admin only)"""
        try:
            if self.supabase is None:
                logger.error("Cannot get total message count: Supabase client is not initialized")
                return 0
                
            result = await self.supabase.rpc('get_total_message_count').execute()
            return result.data[0]['count']
        except Exception as e:
            logger.error(f"Error getting total message count: {e}")
            return 0

    async def get_active_users_count(self, last_days: int = 7) -> int:
        """Get count of active users in last N days (admin only)"""
        try:
            if self.supabase is None:
                logger.error("Cannot get active users count: Supabase client is not initialized")
                return 0
                
            result = await self.supabase.rpc('get_active_users_count', {
                'p_days': last_days
            }).execute()
            return result.data[0]['count']
        except Exception as e:
            logger.error(f"Error getting active users count: {e}")
            return 0

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        try:
            if self.supabase is None:
                logger.error("Cannot authenticate user: Supabase client is not initialized")
                return None
                
            result = await self.supabase.table('account_users').select(
                '*'
            ).eq('email', email).single().execute()
            
            if result.data and pwd_context.verify(password, result.data['hashed_password']):
                return result.data
            return None
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    async def get_account(self, account_id: int) -> Optional[Dict]:
        """Get account by ID"""
        try:
            if self.supabase is None:
                logger.error("Cannot get account: Supabase client is not initialized")
                return None
                
            result = await self.supabase.table('accounts').select(
                '*'
            ).eq('id', account_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            if self.supabase is None:
                logger.error("Cannot get user: Supabase client is not initialized")
                return None
                
            result = await self.supabase.table('account_users').select(
                '*'
            ).eq('id', user_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)

    async def get_or_create_permanent_account(self, user_id: str, email: str, chat_id: int) -> Dict:
        """Get or create permanent account for Supabase user"""
        try:
            # Check if account exists for this user
            result = await self.supabase.from_('accounts').select(
                '*'
            ).eq('supabase_user_id', user_id).single().execute()

            if result.data:
                # Add chat to existing account if not already linked
                await self.link_chat_to_account(result.data['id'], chat_id)
                return result.data

            # Create new account
            account_result = await self.supabase.from_('accounts').insert({
                'supabase_user_id': user_id,
                'name': email.split('@')[0],  # Use email username as initial name
                'email': email
            }).execute()

            account = account_result.data[0]

            # Link chat
            await self.link_chat_to_account(account['id'], chat_id)

            return account

        except Exception as e:
            logger.error(f"Error in get_or_create_permanent_account: {e}")
            raise

    async def link_chat_to_account(self, account_id: int, chat_id: int) -> None:
        """Link a chat to an account"""
        try:
            # Check if already linked
            existing = await self.supabase.from_('account_chats').select(
                '*'
            ).eq('account_id', account_id).eq('telegram_chat_id', chat_id).execute()

            if not existing.data:
                await self.supabase.from_('account_chats').insert({
                    'account_id': account_id,
                    'telegram_chat_id': chat_id
                }).execute()

        except Exception as e:
            logger.error(f"Error linking chat to account: {e}")
            raise 

    async def get_usage_stats(self, account_id: int, period: str = "current") -> Dict:
        """Get usage statistics for an account"""
        try:
            # Calculate period dates
            now = datetime.now()
            if period == "current":
                start_date = now.replace(day=1)
                end_date = now
            else:  # previous
                start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
                end_date = now.replace(day=1) - timedelta(days=1)

            result = await self.supabase.rpc('get_account_usage_stats', {
                'p_account_id': account_id,
                'p_start_date': start_date.isoformat(),
                'p_end_date': end_date.isoformat()
            }).execute()

            if result.data:
                return {
                    "total_tokens": result.data[0]['total_tokens'],
                    "messages": result.data[0]['message_count']
                }
            return {"total_tokens": 0, "messages": 0}
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {"total_tokens": 0, "messages": 0}

    async def track_usage(self, account_id: int, tokens_used: int) -> None:
        """Track token usage for an account"""
        try:
            await self.supabase.table('usage_stats').insert({
                'account_id': account_id,
                'tokens_used': tokens_used,
                'timestamp': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error tracking usage: {e}") 