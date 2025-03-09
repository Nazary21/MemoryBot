import logging
from typing import Optional, Dict, List
from config.database import init_supabase
from datetime import datetime, timedelta
from passlib.context import CryptContext
import os
import json

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Database:
    def __init__(self):
        self.supabase = init_supabase()
        self.initialized = self.supabase is not None
        self.fallback_mode = not self.initialized
        
        if not self.initialized:
            logger.warning("⚠️ FALLBACK MODE ACTIVE: Database operations will use file-based storage")
            self.setup_file_fallback()
            # Migrate any legacy files
            self.migrate_legacy_files()
        else:
            logger.info("✅ Database connection successful")
    
    def setup_file_fallback(self):
        """Set up file-based fallback storage"""
        try:
            # Create base memory directory if it doesn't exist
            self.memory_dir = "memory"
            os.makedirs(self.memory_dir, exist_ok=True)
            
            # Create account-specific directory for default account
            self.account_dir = os.path.join(self.memory_dir, "account_1")
            os.makedirs(self.account_dir, exist_ok=True)
            
            # Create account-specific directory for test account
            test_account_dir = os.path.join(self.memory_dir, "account_0")
            os.makedirs(test_account_dir, exist_ok=True)
            
            # Create default files if they don't exist
            self.fallback_files = {
                'temporary_accounts': os.path.join(self.account_dir, "temporary_accounts.json"),
                'accounts': os.path.join(self.account_dir, "accounts.json"),
                'chat_history': os.path.join(self.account_dir, "chat_history.json"),
                'bot_rules': os.path.join(self.account_dir, "bot_rules.json")
            }
            
            # Initialize files with empty arrays if they don't exist
            for file_path in self.fallback_files.values():
                if not os.path.exists(file_path):
                    with open(file_path, 'w') as f:
                        json.dump([], f)
            
            logger.info("✅ File-based fallback mode set up successfully")
        except Exception as e:
            logger.error(f"Error setting up file-based fallback: {e}")
        
    async def setup_tables(self):
        """Initialize database tables"""
        try:
            if not self.initialized:
                logger.warning("⚠️ Cannot set up tables: Operating in fallback mode")
                return
                
            logger.info("Setting up database tables...")
            
            # Try to check if the bot_rules table exists
            try:
                result = await self.supabase.from_('bot_rules').select('count', count='exact').limit(1).execute()
                logger.info(f"bot_rules table exists, contains {result.count} rules")
                # Even if table exists, we'll continue to make sure all tables are created
            except Exception as check_error:
                logger.info(f"bot_rules table check failed, will create schema: {check_error}")
            
            # Create tables using raw SQL for more control
            tables_created = 0
            try:
                logger.info("Creating database tables if they don't exist...")
                
                # Create bot_rules table
                try:
                    await self.supabase.rpc('execute_sql', {
                        'query': """
                        CREATE TABLE IF NOT EXISTS bot_rules (
                            id SERIAL PRIMARY KEY,
                            account_id INTEGER NOT NULL,
                            rule_text TEXT NOT NULL,
                            priority INTEGER DEFAULT 0,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                        """
                    }).execute()
                    logger.info("bot_rules table created or verified")
                    tables_created += 1
                except Exception as e:
                    logger.error(f"Error creating bot_rules table: {e}")
                
                # Create accounts table if it doesn't exist
                try:
                    await self.supabase.rpc('execute_sql', {
                        'query': """
                        CREATE TABLE IF NOT EXISTS accounts (
                            id SERIAL PRIMARY KEY,
                            name TEXT,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                        """
                    }).execute()
                    logger.info("accounts table created or verified")
                    tables_created += 1
                except Exception as e:
                    logger.error(f"Error creating accounts table: {e}")
                
                # Create temporary_accounts table if it doesn't exist
                try:
                    await self.supabase.rpc('execute_sql', {
                        'query': """
                        CREATE TABLE IF NOT EXISTS temporary_accounts (
                            id SERIAL PRIMARY KEY,
                            telegram_chat_id BIGINT UNIQUE NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            expires_at TIMESTAMP WITH TIME ZONE
                        );
                        """
                    }).execute()
                    logger.info("temporary_accounts table created or verified")
                    tables_created += 1
                except Exception as e:
                    logger.error(f"Error creating temporary_accounts table: {e}")
                
                # Create chat_history table if it doesn't exist
                try:
                    await self.supabase.rpc('execute_sql', {
                        'query': """
                        CREATE TABLE IF NOT EXISTS chat_history (
                            id SERIAL PRIMARY KEY,
                            account_id INTEGER,
                            telegram_chat_id BIGINT,
                            role TEXT NOT NULL,
                            content TEXT NOT NULL,
                            memory_type TEXT DEFAULT 'short_term',
                            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                        """
                    }).execute()
                    logger.info("chat_history table created or verified")
                    tables_created += 1
                except Exception as e:
                    logger.error(f"Error creating chat_history table: {e}")
                
                if tables_created > 0:
                    logger.info(f"✅ Created or verified {tables_created} tables successfully")
                
                # Create default account if it doesn't exist (for backward compatibility)
                try:
                    account_result = await self.supabase.from_('accounts').select('*').eq('id', 1).execute()
                    if not account_result.data:
                        logger.info("Creating default account (id=1)")
                        await self.supabase.from_('accounts').insert({'id': 1, 'name': 'Default Account'}).execute()
                        logger.info("Default account created successfully")
                except Exception as account_error:
                    logger.error(f"Error checking/creating default account: {account_error}")
                
            except Exception as schema_error:
                logger.error(f"Error creating schema: {schema_error}")
                
                # Try alternative approach - direct SQL execution
                try:
                    logger.info("Trying alternative schema creation approach...")
                    # Create minimal bot_rules table for rules to work
                    await self.supabase.rpc('execute_sql', {
                        'sql': "CREATE TABLE IF NOT EXISTS bot_rules (id SERIAL PRIMARY KEY, account_id INTEGER NOT NULL, rule_text TEXT NOT NULL, priority INTEGER DEFAULT 0, is_active BOOLEAN DEFAULT TRUE);"
                    }).execute()
                    logger.info("Alternative schema creation successful")
                except Exception as alt_error:
                    logger.error(f"Alternative schema creation also failed: {alt_error}")
                    logger.warning("⚠️ Switching to fallback mode due to schema creation failure")
                    self.initialized = False
                    self.fallback_mode = True
                    self.setup_file_fallback()
                
        except Exception as e:
            logger.error(f"Error setting up tables: {e}")
            logger.warning("⚠️ Switching to fallback mode due to table setup failure")
            self.initialized = False
            self.fallback_mode = True
            self.setup_file_fallback()

    async def get_or_create_temporary_account(self, chat_id: int) -> Dict:
        """Get or create a temporary account for a chat"""
        try:
            if not self.initialized:
                logger.debug("Using file-based fallback for temporary account")
                return self._get_or_create_temporary_account_fallback(chat_id)
            
            logger.info(f"Database: Checking for existing temporary account for chat_id={chat_id}")
            try:
                # Check for existing temporary account
                result = self.supabase.from_('temporary_accounts').select('*').eq('telegram_chat_id', chat_id).execute()
                
                # Process the result
                if hasattr(result, 'data') and result.data:
                    logger.info(f"Database: Found existing temporary account for chat_id={chat_id}")
                    return result.data[0]
                
                logger.info(f"Database: Creating new temporary account for chat_id={chat_id}")
                # Create new temporary account
                create_result = self.supabase.from_('temporary_accounts').insert({
                    'telegram_chat_id': chat_id,
                    'expires_at': (datetime.now() + timedelta(days=30)).isoformat()
                }).execute()
                
                if hasattr(create_result, 'data') and create_result.data:
                    logger.info(f"Database: Successfully created temporary account for chat_id={chat_id}")
                    return create_result.data[0]
                else:
                    logger.warning(f"Database: Could not create temporary account, using fallback")
                    return self._get_or_create_temporary_account_fallback(chat_id)
            
            except Exception as query_error:
                logger.error(f"Error in Supabase query: {query_error}")
                raise  # Re-raise to be caught by the outer try-except
            
        except Exception as e:
            logger.error(f"Error in get_or_create_temporary_account: {e}")
            # Use fallback method
            return self._get_or_create_temporary_account_fallback(chat_id)
    
    def _get_or_create_temporary_account_fallback(self, chat_id: int) -> Dict:
        """Fallback method to get or create a temporary account using file storage"""
        try:
            # Ensure memory_dir is initialized
            if not hasattr(self, 'memory_dir'):
                self.setup_file_fallback()
                
            # Ensure fallback_files is initialized
            if not hasattr(self, 'fallback_files'):
                self.memory_dir = "memory"
                self.account_dir = os.path.join(self.memory_dir, "account_1")
                self.fallback_files = {
                    'temporary_accounts': os.path.join(self.account_dir, "temporary_accounts.json"),
                    'accounts': os.path.join(self.account_dir, "accounts.json"),
                    'chat_history': os.path.join(self.account_dir, "chat_history.json"),
                    'bot_rules': os.path.join(self.account_dir, "bot_rules.json")
                }
            
            # Load existing temporary accounts
            temporary_accounts = []
            if os.path.exists(self.fallback_files['temporary_accounts']):
                with open(self.fallback_files['temporary_accounts'], 'r') as f:
                    content = f.read().strip()
                    if content:
                        temporary_accounts = json.loads(content)
            
            # Check if account exists
            for account in temporary_accounts:
                if account.get('telegram_chat_id') == chat_id:
                    return account
            
            # Create new account
            expiration_date = (datetime.now() + timedelta(days=30)).isoformat()
            new_account = {
                'id': 1,  # Default to account 1 for fallback
                'telegram_chat_id': chat_id,
                'created_at': datetime.now().isoformat(),
                'expires_at': expiration_date,
                'is_active': True
            }
            
            # For test chat ID, use account 0
            if chat_id == 12345:  # Test chat ID
                new_account['id'] = 0
            
            temporary_accounts.append(new_account)
            
            # Save updated accounts
            with open(self.fallback_files['temporary_accounts'], 'w') as f:
                json.dump(temporary_accounts, f)
            
            return new_account
            
        except Exception as e:
            logger.error(f"Error in fallback temporary account creation: {e}")
            # Return a default account as last resort
            return {
                'id': 1,
                'telegram_chat_id': chat_id,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
                'is_active': True
            }

    async def get_account_by_chat(self, chat_id: int) -> Optional[Dict]:
        """Get permanent account by chat ID"""
        try:
            if not self.initialized:
                logger.warning("Using file-based fallback for get_account_by_chat")
                return None
                
            result = self.supabase.from_('account_chats').select(
                'accounts(*)'
            ).eq('telegram_chat_id', chat_id).execute()
            
            return result.data[0]['accounts'] if result.data else None
            
        except Exception as e:
            logger.error(f"Error in get_account_by_chat: {e}")
            return None

    async def store_chat_message(self, account_id: int, chat_id: int, role: str, content: str, memory_type: str = 'short_term'):
        """Store a chat message"""
        try:
            if not self.initialized:
                logger.warning("Using file-based fallback for store_chat_message")
                self._store_chat_message_fallback(account_id, chat_id, role, content, memory_type)
                return
            
            logger.info(f"Database: Attempting to store message in Supabase (account_id={account_id}, chat_id={chat_id}, memory_type={memory_type})")
            try:
                result = self.supabase.from_('chat_history').insert({
                    'account_id': account_id,
                    'telegram_chat_id': chat_id,
                    'role': role,
                    'content': content,
                    'memory_type': memory_type
                }).execute()
                
                logger.info(f"Database: Successfully stored message in Supabase")
                return True
            except Exception as insert_error:
                logger.error(f"Error inserting into Supabase: {insert_error}")
                raise  # Re-raise to be caught by the outer try-except
            
        except Exception as e:
            logger.error(f"Error storing chat message: {e}")
            logger.info(f"Database: Falling back to file-based storage for message")
            # Use fallback method
            self._store_chat_message_fallback(account_id, chat_id, role, content, memory_type)
    
    def _store_chat_message_fallback(self, account_id: int, chat_id: int, role: str, content: str, memory_type: str):
        """Fallback method to store chat message using file storage"""
        try:
            # Ensure memory_dir is initialized
            if not hasattr(self, 'memory_dir'):
                self.setup_file_fallback()
                
            # Use account-specific directory
            account_dir = os.path.join(self.memory_dir, f"account_{account_id}")
            logger.info(f"Database: Fallback storing message in directory: {account_dir}")
            os.makedirs(account_dir, exist_ok=True)
            
            # Store directly in memory-type specific file
            memory_type_file = os.path.join(account_dir, f"{memory_type}.json")
            logger.info(f"Database: Fallback storing message in file: {memory_type_file}")
            
            # Load existing messages
            memory_type_messages = []
            if os.path.exists(memory_type_file):
                with open(memory_type_file, 'r') as f:
                    content_data = f.read().strip()
                    if content_data:
                        try:
                            data = json.loads(content_data)
                            # Handle both array and empty object formats
                            if isinstance(data, list):
                                memory_type_messages = data
                            elif isinstance(data, dict) and not data:  # Empty object
                                memory_type_messages = []
                            else:
                                logger.warning(f"Unexpected data format in {memory_type_file}, initializing as empty array")
                                memory_type_messages = []
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in {memory_type_file}, initializing as empty array")
                            memory_type_messages = []
            
            # Add new message
            new_message = {
                'id': len(memory_type_messages) + 1,
                'account_id': account_id,
                'telegram_chat_id': chat_id,
                'role': role,
                'content': content,
                'memory_type': memory_type,
                'timestamp': datetime.now().isoformat()
            }
            
            memory_type_messages.append(new_message)
            
            # Limit short_term to 50 messages
            if memory_type == 'short_term' and len(memory_type_messages) > 50:
                memory_type_messages = memory_type_messages[-50:]
            
            # Limit mid_term to 200 messages
            if memory_type == 'mid_term' and len(memory_type_messages) > 200:
                memory_type_messages = memory_type_messages[-200:]
            
            # Save updated memory-type specific messages
            with open(memory_type_file, 'w') as f:
                json.dump(memory_type_messages, f)
                
            logger.info(f"Database: Successfully stored message in fallback file: {memory_type_file}")
            return True
                
        except Exception as e:
            logger.error(f"Error in fallback message storage: {e}")
            return False

    async def get_chat_memory(self, chat_id: int, memory_type: str = 'short_term', limit: Optional[int] = 50) -> List[Dict]:
        """Get chat memory by type"""
        try:
            if not self.initialized:
                logger.warning("Using file-based fallback for get_chat_memory")
                return self._get_chat_memory_fallback(chat_id, memory_type, limit)
            
            logger.info(f"Database: Attempting to retrieve {memory_type} memory for chat_id={chat_id} (limit={limit})")
            query = self.supabase.from_('chat_history').select('*').eq(
                'telegram_chat_id', chat_id
            ).eq('memory_type', memory_type).order('timestamp', desc=True)
            
            # Only apply limit if it's not None
            if limit is not None:
                query = query.limit(limit)
            
            try:
                result = query.execute()
                logger.info(f"Database: Successfully retrieved messages from Supabase")
                # Check if result has data attribute
                if hasattr(result, 'data'):
                    logger.info(f"Database: Found {len(result.data)} messages")
                    return result.data
                else:
                    # Try to access data as dictionary
                    logger.info(f"Database: Trying to access data as dictionary")
                    data = getattr(result, 'json', lambda: {})()
                    if isinstance(data, dict) and 'data' in data:
                        logger.info(f"Database: Found {len(data['data'])} messages in dictionary")
                        return data['data']
                    else:
                        logger.warning(f"Database: Could not extract data from response, using empty list")
                        return []
            except Exception as query_error:
                logger.error(f"Error executing query: {query_error}")
                return []
            
        except Exception as e:
            logger.error(f"Error getting chat memory: {e}")
            logger.info(f"Database: Falling back to file-based retrieval for memory")
            return self._get_chat_memory_fallback(chat_id, memory_type, limit)
    
    def _get_chat_memory_fallback(self, chat_id: int, memory_type: str, limit: Optional[int]) -> List[Dict]:
        """Fallback method to get chat memory using file storage"""
        try:
            # Ensure memory_dir is initialized
            if not hasattr(self, 'memory_dir'):
                self.setup_file_fallback()
                
            # Get account for this chat
            account = self._get_or_create_temporary_account_fallback(chat_id)
            account_id = account.get('id', 1)
            
            # Use account-specific directory
            account_dir = os.path.join(self.memory_dir, f"account_{account_id}")
            memory_type_file = os.path.join(account_dir, f"{memory_type}.json")
            
            logger.info(f"Database: Fallback retrieving messages from file: {memory_type_file}")
            
            # Load messages from file
            if os.path.exists(memory_type_file):
                with open(memory_type_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        try:
                            messages = json.loads(content)
                            if isinstance(messages, list):
                                # Apply limit if specified
                                if limit and len(messages) > limit:
                                    messages = messages[-limit:]
                                logger.info(f"Database: Successfully retrieved {len(messages)} messages from fallback file")
                                return messages
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in {memory_type_file}")
            
            # Return empty list if no messages found
            logger.info("Database: No messages found in fallback file")
            return []
            
        except Exception as e:
            logger.error(f"Error in fallback memory retrieval: {e}")
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
            account_result = await self.supabase.from_('accounts').insert({
                'name': name
            }).execute()
            
            if not account_result.data:
                logger.error("Failed to create account")
                return {}
                
            account = account_result.data[0]
            
            # Create user
            await self.supabase.from_('account_users').insert({
                'account_id': account['id'],
                'email': email,
                'hashed_password': hashed_password
            }).execute()
            
            # Link chat
            await self.supabase.from_('account_chats').insert({
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
            await self.supabase.from_('chat_history').insert({
                'account_id': new_account_id,
                'telegram_chat_id': temp_account['telegram_chat_id'],
                'role': 'system',
                'content': 'Account migrated from temporary to permanent',
                'memory_type': 'system'
            }).execute()
            
            # Mark old account as migrated
            await self.supabase.from_('migration_mapping').insert({
                'old_chat_id': chat_id,
                'new_account_id': new_account_id,
                'migration_status': 'completed'
            }).execute()
            
            # Delete temporary account
            await self.supabase.from_('temporary_accounts').delete().eq('id', temp_account['id']).execute()
            
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
                
            result = await self.supabase.from_('chat_history').select('*').eq(
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
                
            await self.supabase.from_('history_context').insert({
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
                
            result = await self.supabase.from_('history_context').select('*').eq(
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
                
            await self.supabase.from_('chat_history').delete().eq(
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
                
            result = await self.supabase.from_('accounts').select(
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
                
            result = await self.supabase.from_('account_users').select(
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
                
            result = await self.supabase.from_('accounts').select(
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
                
            result = await self.supabase.from_('account_users').select(
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
            await self.supabase.from_('usage_stats').insert({
                'account_id': account_id,
                'tokens_used': tokens_used,
                'timestamp': datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")

    def is_in_fallback_mode(self) -> bool:
        """Check if database is operating in fallback mode"""
        return self.fallback_mode 

    def migrate_legacy_files(self):
        """Migrate files from root directory to account-specific directories"""
        try:
            # Files to migrate
            legacy_files = {
                'temporary_accounts.json': 'temporary_accounts.json',
                'accounts.json': 'accounts.json',
                'chat_history.json': 'chat_history.json',
                'bot_rules.json': 'bot_rules.json',
                'short_term.json': 'short_term.json',
                'mid_term.json': 'mid_term.json',
                'whole_history.json': 'whole_history.json',
                'history_context.json': 'history_context.json'
            }
            
            # Create account-specific directory
            account_dir = os.path.join(self.memory_dir, "account_1")
            os.makedirs(account_dir, exist_ok=True)
            
            # Migrate each file
            for old_name, new_name in legacy_files.items():
                old_path = os.path.join(self.memory_dir, old_name)
                new_path = os.path.join(account_dir, new_name)
                
                if os.path.exists(old_path) and not os.path.exists(new_path):
                    # Read old file
                    try:
                        with open(old_path, 'r') as f:
                            data = json.load(f)
                        
                        # Save to new location
                        with open(new_path, 'w') as f:
                            json.dump(data, f, indent=2)
                        
                        # Rename old file to .migrated
                        migrated_path = old_path + '.migrated'
                        os.rename(old_path, migrated_path)
                        
                        logger.info(f"Migrated {old_name} to account-specific directory")
                    except Exception as e:
                        logger.error(f"Error migrating {old_name}: {e}")
                        continue
            
            logger.info("✅ Legacy file migration completed")
        except Exception as e:
            logger.error(f"❌ Error during legacy file migration: {e}") 