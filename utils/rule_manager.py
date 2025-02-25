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
            {"text": "Be helpful, concise, and friendly.", "priority": 10, "category": "General"},
            {"text": "Respond in the same language as the user's message.", "priority": 9, "category": "Language"},
            {"text": "If you learn someone's name, use it in future responses.", "priority": 8, "category": "Personalization"},
            {"text": "Keep track of important information shared in conversation.", "priority": 7, "category": "Memory"},
            {"text": "Be respectful and maintain a positive tone.", "priority": 6, "category": "Tone"}
        ]

    async def get_rules(self, account_id: int = 1) -> List[Rule]:
        """Get active rules for an account"""
        try:
            # Check if Supabase client is initialized
            if self.db.supabase is None:
                logger.error("Cannot get rules: Supabase client is not initialized")
                # Use file-based fallback
                return self._get_rules_fallback(account_id)
                
            result = await self.db.supabase.from_('bot_rules').select(
                '*'
            ).eq('account_id', account_id).eq('is_active', True).order('priority', desc=True).execute()
            
            # If no rules found, create default rules
            if not result.data:
                logger.info(f"No rules found for account {account_id}. Creating default rules.")
                await self.create_default_rules(account_id)
                
                # Try to get rules again
                result = await self.db.supabase.from_('bot_rules').select(
                    '*'
                ).eq('account_id', account_id).eq('is_active', True).order('priority', desc=True).execute()
            
            return [Rule(
                text=rule['rule_text'],
                priority=rule['priority'],
                is_active=rule['is_active']
            ) for rule in result.data]
        except Exception as e:
            logger.error(f"Error getting rules: {e}")
            # Use file-based fallback
            return self._get_rules_fallback(account_id)
        
    def _get_rules_fallback(self, account_id: int) -> List[Rule]:
        """Fallback method to get rules using file storage"""
        try:
            # Create memory directory if it doesn't exist
            memory_dir = "memory"
            os.makedirs(memory_dir, exist_ok=True)
            
            # Create rules file if it doesn't exist
            rules_file = os.path.join(memory_dir, "bot_rules.json")
            
            # Check if file exists
            if not os.path.exists(rules_file):
                # Create default rules
                self._create_default_rules_fallback(account_id)
            
            # Load rules
            with open(rules_file, 'r') as f:
                try:
                    all_rules = json.load(f)
                except json.JSONDecodeError:
                    all_rules = []
            
            # Filter rules for this account
            account_rules = [
                rule for rule in all_rules 
                if rule.get('account_id') == account_id and rule.get('is_active', True)
            ]
            
            # Sort by priority
            account_rules.sort(key=lambda x: x.get('priority', 0), reverse=True)
            
            # Convert to Rule objects
            return [Rule(
                text=rule.get('rule_text', ''),
                priority=rule.get('priority', 0),
                is_active=True
            ) for rule in account_rules]
        except Exception as e:
            logger.error(f"Error in fallback rules retrieval: {e}")
            # Return default rules directly as a last resort
            return [Rule(text=rule["text"], priority=rule["priority"]) 
                    for rule in self.default_rules]

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
            # Create memory directory if it doesn't exist
            memory_dir = "memory"
            os.makedirs(memory_dir, exist_ok=True)
            
            # Create rules file if it doesn't exist
            rules_file = os.path.join(memory_dir, "bot_rules.json")
            
            # Load existing rules
            rules = []
            if os.path.exists(rules_file):
                with open(rules_file, 'r') as f:
                    try:
                        rules = json.load(f)
                    except json.JSONDecodeError:
                        rules = []
            
            # Add default rules for this account
            for rule in self.default_rules:
                rules.append({
                    'account_id': account_id,
                    'rule_text': rule["text"],
                    'priority': rule["priority"],
                    'is_active': True,
                    'created_at': datetime.now().isoformat()
                })
            
            # Save updated rules
            with open(rules_file, 'w') as f:
                json.dump(rules, f)
            
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
        if rules is None:
            # For backward compatibility
            return "No active rules configured."
            
        if not rules:
            return "No active rules configured."
            
        formatted = "Current Bot Rules:\n\n"
        for i, rule in enumerate(rules, 1):
            formatted += f"{i}. {rule.text}"
            if rule.priority > 0:
                formatted += f" (Priority: {rule.priority})"
            formatted += "\n"
        return formatted

    async def add_rule(self, account_id: int, rule_text: str, category: str = "General", priority: int = 0) -> Optional[Rule]:
        """Add a new rule for an account"""
        try:
            if self.db.supabase is None:
                logger.error("Cannot add rule: Supabase client is not initialized")
                # Use file-based fallback
                return self._add_rule_fallback(account_id, rule_text, category, priority)
                
            # Try to insert the rule
            try:
                result = await self.db.supabase.from_('bot_rules').insert({
                    'account_id': account_id,
                    'rule_text': rule_text,
                    'priority': priority,
                    'is_active': True
                }).execute()
                
                if result.data:
                    rule_data = result.data[0]
                    logger.info(f"Rule added successfully: {rule_text}")
                    return Rule(
                        text=rule_data['rule_text'],
                        priority=rule_data['priority'],
                        is_active=rule_data['is_active']
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
                        INSERT INTO bot_rules (account_id, rule_text, priority, is_active)
                        VALUES ({account_id}, '{rule_text.replace("'", "''")}', {priority}, TRUE)
                        """
                    }).execute()
                    logger.info(f"Rule added via SQL: {rule_text}")
                    return Rule(text=rule_text, priority=priority, is_active=True)
                except Exception as sql_error:
                    logger.error(f"Error adding rule via SQL: {sql_error}")
            
            # If we get here, both attempts failed
            return self._add_rule_fallback(account_id, rule_text, category, priority)
        except Exception as e:
            logger.error(f"Error adding rule: {e}")
            return self._add_rule_fallback(account_id, rule_text, category, priority)
    
    def _add_rule_fallback(self, account_id: int, rule_text: str, category: str, priority: int) -> Optional[Rule]:
        """Fallback method to add a rule using file storage"""
        try:
            logger.info(f"Using file-based fallback to add rule: {rule_text}")
            
            # Create memory directory if it doesn't exist
            memory_dir = "memory"
            os.makedirs(memory_dir, exist_ok=True)
            
            # Create rules file if it doesn't exist
            rules_file = os.path.join(memory_dir, "bot_rules.json")
            
            # Load existing rules
            rules = []
            if os.path.exists(rules_file):
                with open(rules_file, 'r') as f:
                    try:
                        rules = json.load(f)
                    except json.JSONDecodeError:
                        rules = []
            
            # Add new rule
            new_rule = {
                'account_id': account_id,
                'rule_text': rule_text,
                'category': category,
                'priority': priority,
                'is_active': True,
                'created_at': datetime.now().isoformat()
            }
            
            rules.append(new_rule)
            
            # Save updated rules
            with open(rules_file, 'w') as f:
                json.dump(rules, f)
            
            logger.info(f"Rule added to file storage: {rule_text}")
            return Rule(text=rule_text, priority=priority, is_active=True)
        except Exception as e:
            logger.error(f"Error in fallback rule addition: {e}")
            return None

    async def update_rule(self, rule_id: int, account_id: int, updates: Dict) -> bool:
        """Update an existing rule"""
        try:
            await self.db.supabase.from_('bot_rules').update(
                updates
            ).eq('id', rule_id).eq('account_id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating rule: {e}")
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
        """Fallback method to delete a rule using file storage"""
        try:
            logger.info(f"Using file-based fallback to delete rule at index {rule_index}")
            
            # Create memory directory if it doesn't exist
            memory_dir = "memory"
            os.makedirs(memory_dir, exist_ok=True)
            
            # Create rules file if it doesn't exist
            rules_file = os.path.join(memory_dir, "bot_rules.json")
            
            # Check if file exists
            if not os.path.exists(rules_file):
                logger.error("Rules file doesn't exist")
            return False

            # Load existing rules
            with open(rules_file, 'r') as f:
                try:
                    all_rules = json.load(f)
                except json.JSONDecodeError:
                    all_rules = []
            
            # Filter rules for this account
            account_rules = [
                rule for rule in all_rules 
                if rule.get('account_id') == account_id and rule.get('is_active', True)
            ]
            
            # Sort by priority
            account_rules.sort(key=lambda x: x.get('priority', 0), reverse=True)
            
            if rule_index < 0 or rule_index >= len(account_rules):
                logger.error(f"Invalid rule index: {rule_index}, total rules: {len(account_rules)}")
                return False
            
            # Get the rule to delete
            rule_to_delete = account_rules[rule_index]
            
            # Remove the rule from all_rules
            all_rules = [
                rule for rule in all_rules 
                if not (rule.get('account_id') == account_id and 
                        rule.get('rule_text') == rule_to_delete.get('rule_text') and
                        rule.get('priority') == rule_to_delete.get('priority'))
            ]
            
            # Save updated rules
            with open(rules_file, 'w') as f:
                json.dump(all_rules, f)
            
            logger.info(f"Rule deleted from file storage")
            return True
        except Exception as e:
            logger.error(f"Error in fallback rule deletion: {e}")
            return False 