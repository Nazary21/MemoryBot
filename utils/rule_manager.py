import json
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Rule:
    text: str
    priority: int = 0
    is_active: bool = True
    category: str = "General"

class GPTRule:
    def __init__(self, text: str, category: str = "General", priority: int = 0):
        self.text = text
        self.category = category
        self.priority = priority
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "category": self.category,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GPTRule':
        rule = cls(
            text=data.get("text") or data.get("rule", ""),  # Handle both new and old format
            category=data.get("category", "General"),
            priority=data.get("priority", 0)
        )
        rule.created_at = data.get("created_at", rule.created_at)
        rule.updated_at = data.get("updated_at", rule.updated_at)
        return rule

class RuleManager:
    def __init__(self, db):
        self.db = db
        # Default rules that will be created for new accounts
        self.default_rules = [
            {"text": "Respond in the same language as the user's message.", "priority": 1, "category": "Language"},
            {"text": "If you learn someone's name, use it in future responses.", "priority": 1, "category": "Personalization"},
            {"text": "Keep track of important information shared in conversation.", "priority": 1, "category": "Memory"}
        ]
        # Try to migrate any legacy rules when manager is created
        self._migrate_legacy_rules()

    async def get_rules(self, account_id: int = 1) -> List[Rule]:
        """Get active rules for an account"""
        rules = []
        try:
            logger.info(f"Getting rules for account {account_id}")
            
            if self.db.supabase is None:
                logger.info("Database not available, using fallback storage")
                return self._get_rules_fallback(account_id)
            
            # Get account-specific rules
            logger.info(f"Fetching account-specific rules for account {account_id}")
            result = await self.db.supabase.from_('bot_rules').select(
                '*'
            ).eq('account_id', account_id).eq('is_active', True).order('priority', desc=True).execute()
            
            logger.info(f"Found {len(result.data)} account-specific rules")
            
            # Get global rules from account 1 if this is not account 1
            if account_id != 1:
                logger.info("Fetching global rules from account 1")
                global_result = await self.db.supabase.from_('bot_rules').select(
                    '*'
                ).eq('account_id', 1).eq('is_active', True).order('priority', desc=True).execute()
                
                logger.info(f"Found {len(global_result.data)} global rules")
                
                # Add global rules first (they have lower priority)
                rules.extend([Rule(
                    text=rule['rule_text'],
                    priority=rule['priority'],
                    is_active=rule['is_active'],
                    category=rule.get('category', 'General')
                ) for rule in global_result.data])
                logger.info(f"Added {len(global_result.data)} global rules")
            
            # Add account-specific rules (they have higher priority)
            rules.extend([Rule(
                text=rule['rule_text'],
                priority=rule['priority'],
                is_active=rule['is_active'],
                category=rule.get('category', 'General')
            ) for rule in result.data])
            logger.info(f"Added {len(result.data)} account-specific rules")
            
            # Log final rule set
            logger.info(f"Total rules for account {account_id}: {len(rules)}")
            for rule in rules:
                logger.info(f"Rule: {rule.text[:50]}... (Priority: {rule.priority})")
            
            return rules
        except Exception as e:
            logger.error(f"Error getting rules: {e}")
            # Use file-based fallback
            return self._get_rules_fallback(account_id)
        
    def _get_rules_fallback(self, account_id: int) -> List[Rule]:
        """Get rules from account-specific file storage when database is not available"""
        try:
            # Only use account-specific directory
            account_dir = f"memory/account_{account_id}"
            account_rules_file = os.path.join(account_dir, "bot_rules.json")
            
            rules = []
            
            # Try to get rules from the account-specific directory
            if os.path.exists(account_rules_file):
                with open(account_rules_file, 'r') as f:
                    try:
                        rules = json.load(f)
                    except json.JSONDecodeError:
                        logger.error(f"Error reading rules from {account_rules_file}")
                        rules = []
            
            # If no rules found, create default rules
            if not rules:
                logger.info(f"No rules found for account {account_id}, creating defaults")
                if self._create_default_rules_fallback(account_id):
                    with open(account_rules_file, 'r') as f:
                        try:
                            rules = json.load(f)
                        except json.JSONDecodeError:
                            logger.error("Error reading newly created default rules")
                            rules = []
            
            # Convert the rules to Rule objects
            return [Rule(
                text=rule['rule_text'],
                priority=rule.get('priority', 0),
                is_active=rule.get('is_active', True),
                category=rule.get('category', 'General')
            ) for rule in rules]
            
        except Exception as e:
            logger.error(f"Error getting rules from files: {e}")
            return []

    async def create_default_rules(self, account_id: int) -> bool:
        """Create default rules for a new account"""
        try:
            if self.db.supabase is None:
                logger.error("Cannot create default rules: Supabase client is not initialized")
                logger.info("Using file-based fallback for default rules")
                return self._create_default_rules_fallback(account_id)
                
            # Check if account exists
            try:
                account_result = await self.db.supabase.from_('accounts').select('*').eq('id', account_id).execute()
                
                # If account doesn't exist, create it
                if not account_result.data:
                    logger.info(f"Account {account_id} doesn't exist. Creating it.")
                    await self.db.supabase.from_('accounts').insert({'id': account_id, 'name': f'Account {account_id}'}).execute()
            except Exception as account_error:
                logger.error(f"Error checking/creating account: {account_error}")
                # Continue anyway to try to create rules
            
            # Check if rules already exist for this account
            try:
                existing_rules = await self.db.supabase.from_('bot_rules').select('*').eq('account_id', account_id).execute()
                if existing_rules.data and len(existing_rules.data) > 0:
                    logger.info(f"Account {account_id} already has {len(existing_rules.data)} rules. Skipping default rule creation.")
                    return True
            except Exception as check_error:
                logger.error(f"Error checking existing rules: {check_error}")
                # Continue to create rules anyway
            
            # Add default rules
            success_count = 0
            for rule in self.default_rules:
                try:
                    # Try direct insert first
                    try:
                        result = await self.db.supabase.from_('bot_rules').insert({
                            'account_id': account_id,
                            'rule_text': rule["text"],
                            'priority': rule["priority"],
                            'is_active': True
                        }).execute()
                        
                        if result.data:
                            success_count += 1
                            logger.info(f"Added rule: {rule['text']}")
                        else:
                            logger.warning(f"Failed to add rule: {rule['text']} - no data returned")
                    except Exception as insert_error:
                        logger.error(f"Error inserting rule '{rule['text']}': {insert_error}")
                        
                        # Try alternative approach with RPC
                        try:
                            await self.db.supabase.rpc('execute_sql', {
                                'query': f"""
                                INSERT INTO bot_rules (account_id, rule_text, priority, is_active)
                                VALUES ({account_id}, '{rule['text'].replace("'", "''")}', {rule['priority']}, TRUE)
                                """
                            }).execute()
                            success_count += 1
                            logger.info(f"Added rule via SQL: {rule['text']}")
                        except Exception as sql_error:
                            logger.error(f"Error adding rule via SQL: {sql_error}")
                except Exception as rule_error:
                    logger.error(f"Error adding rule '{rule['text']}': {rule_error}")
                
            logger.info(f"Default rules created for account {account_id}: {success_count}/{len(self.default_rules)} successful")
            
            # If no rules were added successfully, use fallback
            if success_count == 0:
                logger.warning(f"No rules were added successfully for account {account_id}. Using fallback.")
                return self._create_default_rules_fallback(account_id)
                
            return success_count > 0
        except Exception as e:
            logger.error(f"Error creating default rules: {e}")
            return self._create_default_rules_fallback(account_id)
        
    def _create_default_rules_fallback(self, account_id: int) -> bool:
        """Fallback method to create default rules using file storage"""
        try:
            # Use account-specific directory
            memory_dir = f"memory/account_{account_id}"
            os.makedirs(memory_dir, exist_ok=True)
            
            # Store rules in account directory
            rules_file = os.path.join(memory_dir, "bot_rules.json")
            
            # Load existing rules if any
            rules = []
            if os.path.exists(rules_file):
                with open(rules_file, 'r') as f:
                    try:
                        rules = json.load(f)
                    except json.JSONDecodeError:
                        rules = []
            
            # Add default rules
            for rule in self.default_rules:
                rules.append({
                    'account_id': account_id,  # Include account_id in each rule
                    'rule_text': rule["text"],
                    'priority': rule["priority"],
                    'is_active': True,
                    'category': rule.get("category", "General"),
                    'created_at': datetime.now().isoformat()
                })
            
            # Save updated rules
            with open(rules_file, 'w') as f:
                json.dump(rules, f, indent=2)
            
            logger.info(f"Default rules created in file storage for account {account_id}")
            return True
        except Exception as e:
            logger.error(f"Error in fallback default rules creation: {e}")
            return False

    # For backward compatibility with old code
    def get_rules_sync(self) -> List[GPTRule]:
        """Get rules synchronously (for backward compatibility)"""
        try:
            # Return empty list for backward compatibility
            return []
        except Exception as e:
            logger.error(f"Error getting rules synchronously: {e}")
            return []

    def get_formatted_rules(self, rules: List[Rule] = None) -> str:
        """Format rules for display"""
        try:
            logger.info(f"Formatting {len(rules) if rules else 0} rules")
            
            if rules is None or not rules:
                logger.warning("No rules provided for formatting")
                return "No active rules found."
                
            # Group rules by category
            rules_by_category = {}
            for rule in rules:
                category = getattr(rule, 'category', 'General')  # Default to General if no category
                if category not in rules_by_category:
                    rules_by_category[category] = []
                rules_by_category[category].append(rule)
            
            # Format output
            formatted = "Current Bot Rules:\n\n"
            for category, category_rules in rules_by_category.items():
                formatted += f"{category}:\n"
                for i, rule in enumerate(category_rules, 1):
                    formatted += f"{i}. {rule.text}"
                    if rule.priority == 0:  # Only show if inactive
                        formatted += " (Inactive)"
                    formatted += "\n"
                formatted += "\n"
            
            logger.info(f"Formatted {len(rules)} rules in {len(rules_by_category)} categories")
            return formatted.strip()
        except Exception as e:
            logger.error(f"Error formatting rules: {e}")
            return "Error formatting rules."

    async def add_rule(self, account_id: int, rule_text: str, category: str = "General", priority: int = 0) -> Optional[Rule]:
        """Add a new rule for an account"""
        try:
            if self.db.supabase is None:
                logger.error("Cannot add rule: Supabase client is not initialized")
                # Use file-based fallback
                return self._add_rule_fallback(account_id, rule_text, category, priority)
                
            # Ensure database schema is up to date
            await self._migrate_add_category_column()
                
            # Try to insert the rule
            try:
                result = await self.db.supabase.from_('bot_rules').insert({
                    'account_id': account_id,
                    'rule_text': rule_text,
                    'priority': priority,
                    'is_active': True,
                    'category': category
                }).execute()
                
                if result.data:
                    rule_data = result.data[0]
                    logger.info(f"Rule added successfully: {rule_text}")
                    return Rule(
                        text=rule_data['rule_text'],
                        priority=rule_data['priority'],
                        is_active=rule_data['is_active'],
                        category=rule_data.get('category', 'General')
                    )
                else:
                    logger.warning("No data returned from rule insertion")
            except Exception as insert_error:
                logger.error(f"Error inserting rule: {insert_error}")
                
                # Try alternative approach with RPC
                try:
                    logger.info("Trying alternative rule insertion with RPC...")
                    await self.db.supabase.rpc('execute_sql', {
                        'query': f"""
                        INSERT INTO bot_rules (account_id, rule_text, priority, is_active, category)
                        VALUES ({account_id}, '{rule_text.replace("'", "''")}', {priority}, TRUE, '{category.replace("'", "''")}')
                        """
                    }).execute()
                    logger.info(f"Rule added via SQL: {rule_text}")
                    return Rule(text=rule_text, priority=priority, is_active=True, category=category)
                except Exception as sql_error:
                    logger.error(f"Error adding rule via SQL: {sql_error}")
            
            # If we get here, both attempts failed
            return self._add_rule_fallback(account_id, rule_text, category, priority)
        except Exception as e:
            logger.error(f"Error adding rule: {e}")
            return self._add_rule_fallback(account_id, rule_text, category, priority)
    
    def _add_rule_fallback(self, account_id: int, rule_text: str, category: str, priority: int) -> Optional[Rule]:
        """Add a new rule to file storage when database is not available"""
        try:
            # Create account-specific directory for storing rules
            account_dir = f"memory/account_{account_id}"
            os.makedirs(account_dir, exist_ok=True)
            account_rules_file = os.path.join(account_dir, "bot_rules.json")
            
            # Load existing rules or start with empty list
            rules = []
            if os.path.exists(account_rules_file):
                with open(account_rules_file, 'r') as f:
                    try:
                        rules = json.load(f)
                    except json.JSONDecodeError:
                        rules = []
            
            # Create the new rule with all necessary information
            new_rule = {
                'rule_text': rule_text,
                'priority': priority,
                'is_active': True,
                'category': category,
                'account_id': account_id,
                'created_at': datetime.now().isoformat()
            }
            
            # Add the new rule to our list
            rules.append(new_rule)
            
            # Save all rules back to the file
            with open(account_rules_file, 'w') as f:
                json.dump(rules, f, indent=2)
            
            logger.info(f"Added new rule for account {account_id}: {rule_text}")
            
            # Return a Rule object for immediate use
            return Rule(
                text=rule_text,
                priority=priority,
                is_active=True,
                category=category
            )
        except Exception as e:
            logger.error(f"Error adding rule to file storage: {e}")
            return None

    async def update_rule(self, rule_id: int, account_id: int, updates: Dict) -> bool:
        """Update an existing rule"""
        try:
            if self.db.supabase is None:
                logger.error("Cannot update rule: Supabase client is not initialized")
                # Use file-based fallback
                return await self._update_rule_fallback(rule_id, account_id, updates)
                
            await self.db.supabase.from_('bot_rules').update(
                updates
            ).eq('id', rule_id).eq('account_id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating rule: {e}")
            return await self._update_rule_fallback(rule_id, account_id, updates)

    async def _update_rule_fallback(self, rule_id: int, account_id: int, updates: Dict) -> bool:
        """Update an existing rule in file storage when database is not available"""
        try:
            # Set up the account-specific directory and file paths
            account_dir = f"memory/account_{account_id}"
            account_rules_file = os.path.join(account_dir, "bot_rules.json")
            
            # Make sure the directory exists
            os.makedirs(account_dir, exist_ok=True)
            
            # Load existing rules
            rules = []
            if os.path.exists(account_rules_file):
                with open(account_rules_file, 'r') as f:
                    try:
                        rules = json.load(f)
                    except json.JSONDecodeError:
                        rules = []
            
            # Find and update the specific rule
            updated = False
            for rule in rules:
                if rule.get('id') == rule_id:
                    rule.update(updates)
                    updated = True
                    break
            
            if not updated:
                logger.error(f"Could not find rule {rule_id} to update")
                return False
            
            # Save the updated rules back to file
            with open(account_rules_file, 'w') as f:
                json.dump(rules, f, indent=2)
            
            logger.info(f"Updated rule {rule_id} for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating rule in file storage: {e}")
            return False

    async def delete_rule(self, rule_index: int, account_id: int) -> bool:
        """Delete a rule by index"""
        try:
            if self.db.supabase is None:
                logger.error("Cannot delete rule: Supabase client is not initialized")
                # Use file-based fallback
                return self._delete_rule_fallback(rule_index, account_id)
                
            # Get all rules first
            rules = await self.get_rules(account_id)
            
            if rule_index < 0 or rule_index >= len(rules):
                logger.error(f"Invalid rule index: {rule_index}, total rules: {len(rules)}")
                return False
            
            # We need to find the actual rule ID in the database
            # Since we don't have it directly, we'll try to match by text and priority
            rule = rules[rule_index]
            
            try:
                # Try to find the rule by text and account_id
                result = await self.db.supabase.from_('bot_rules').select('*').eq(
                    'account_id', account_id
                ).eq('rule_text', rule.text).execute()
                
                if result.data:
                    rule_id = result.data[0]['id']
                    logger.info(f"Found rule ID {rule_id} for deletion")
                    
                    # Delete the rule
                    await self.db.supabase.from_('bot_rules').delete().eq('id', rule_id).execute()
                    logger.info(f"Rule {rule_id} deleted successfully")
                    return True
                else:
                    logger.error(f"Could not find rule with text '{rule.text}' for account {account_id}")
                    # Try fallback
                    return self._delete_rule_fallback(rule_index, account_id)
            except Exception as db_error:
                logger.error(f"Database error deleting rule: {db_error}")
                # Try fallback
                return self._delete_rule_fallback(rule_index, account_id)
        except Exception as e:
            logger.error(f"Error deleting rule: {e}")
            return self._delete_rule_fallback(rule_index, account_id)
    
    def _delete_rule_fallback(self, rule_index: int, account_id: int) -> bool:
        """Delete a rule from file storage when database is not available"""
        try:
            # Set up the account-specific directory and file paths
            account_dir = f"memory/account_{account_id}"
            account_rules_file = os.path.join(account_dir, "bot_rules.json")
            
            # Check if we have any rules to delete
            if not os.path.exists(account_rules_file):
                logger.error(f"No rules file found for account {account_id}")
                return False
            
            # Load existing rules
            with open(account_rules_file, 'r') as f:
                try:
                    rules = json.load(f)
                except json.JSONDecodeError:
                    logger.error("Error reading rules file")
                    return False
            
            # Make sure the rule index is valid
            if rule_index < 0 or rule_index >= len(rules):
                logger.error(f"Invalid rule index {rule_index}, total rules: {len(rules)}")
                return False
            
            # Remove the rule at the specified index
            removed_rule = rules.pop(rule_index)
            
            # Save the updated rules back to file
            with open(account_rules_file, 'w') as f:
                json.dump(rules, f, indent=2)
            
            logger.info(f"Deleted rule at index {rule_index} for account {account_id}: {removed_rule.get('rule_text', '')}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting rule from file storage: {e}")
            return False

    async def _migrate_add_category_column(self):
        """Add category column to bot_rules table if it doesn't exist"""
        try:
            if self.db.supabase is None:
                logger.warning("Skipping migration: Supabase client not initialized")
                return False

            # Add category column if it doesn't exist
            await self.db.supabase.rpc('execute_sql', {
                'query': """
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'bot_rules' 
                        AND column_name = 'category'
                    ) THEN
                        ALTER TABLE bot_rules 
                        ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'General';
                    END IF;
                END $$;
                """
            }).execute()
            
            # Update existing rules with their proper categories
            for rule in self.default_rules:
                await self.db.supabase.rpc('execute_sql', {
                    'query': f"""
                    UPDATE bot_rules 
                    SET category = '{rule['category']}' 
                    WHERE rule_text = '{rule['text'].replace("'", "''")}' 
                    AND category = 'General';
                    """
                }).execute()
            
            logger.info("Database migration completed successfully")
            return True
        except Exception as e:
            logger.error(f"Migration error: {e}")
            return False

    def _migrate_legacy_rules(self):
        """Ensure account-specific rules directory exists with proper rules"""
        try:
            account_dir = os.path.join("memory", f"account_1")
            new_rules_file = os.path.join(account_dir, "bot_rules.json")

            # If rules already exist, nothing to do
            if os.path.exists(new_rules_file):
                logger.info("Rules already exist in account directory")
                return

            # Create account directory and default rules
            logger.info("Creating default rules in account directory")
            self._create_default_rules_fallback(account_id=1)
        except Exception as e:
            logger.error(f"Error ensuring rules exist: {e}")
            # Ensure default rules exist even if there's an error
            self._create_default_rules_fallback(account_id=1) 