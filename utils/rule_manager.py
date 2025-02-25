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
                # Return empty list to avoid errors
                return []
                
            result = await self.db.supabase.table('bot_rules').select(
                '*'
            ).eq('account_id', account_id).eq('is_active', True).order('priority', desc=True).execute()
            
            # If no rules found, create default rules
            if not result.data:
                logger.info(f"No rules found for account {account_id}. Creating default rules.")
                await self.create_default_rules(account_id)
                
                # Try to get rules again
                result = await self.db.supabase.table('bot_rules').select(
                    '*'
                ).eq('account_id', account_id).eq('is_active', True).order('priority', desc=True).execute()
            
            return [Rule(
                text=rule['rule_text'],
                priority=rule['priority'],
                is_active=rule['is_active']
            ) for rule in result.data]
        except Exception as e:
            logger.error(f"Error getting rules: {e}")
            return []

    async def create_default_rules(self, account_id: int) -> bool:
        """Create default rules for a new account"""
        try:
            if self.db.supabase is None:
                logger.error("Cannot create default rules: Supabase client is not initialized")
                return False
                
            # Check if account exists
            account_result = await self.db.supabase.table('accounts').select('*').eq('id', account_id).execute()
            
            # If account doesn't exist, create it
            if not account_result.data:
                logger.info(f"Account {account_id} doesn't exist. Creating it.")
                await self.db.supabase.table('accounts').insert({'id': account_id, 'name': f'Account {account_id}'}).execute()
            
            # Add default rules
            for rule in self.default_rules:
                await self.add_rule(
                    account_id=account_id,
                    rule_text=rule["text"],
                    priority=rule["priority"]
                )
                
            logger.info(f"Default rules created for account {account_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating default rules: {e}")
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

    async def add_rule(self, account_id: int, rule_text: str, priority: int = 0) -> Optional[Rule]:
        """Add a new rule for an account"""
        try:
            result = await self.db.supabase.table('bot_rules').insert({
                'account_id': account_id,
                'rule_text': rule_text,
                'priority': priority
            }).execute()
            
            rule_data = result.data[0]
            return Rule(
                text=rule_data['rule_text'],
                priority=rule_data['priority'],
                is_active=rule_data['is_active']
            )
        except Exception as e:
            logger.error(f"Error adding rule: {e}")
            return None

    async def update_rule(self, rule_id: int, account_id: int, updates: Dict) -> bool:
        """Update an existing rule"""
        try:
            await self.db.supabase.table('bot_rules').update(
                updates
            ).eq('id', rule_id).eq('account_id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating rule: {e}")
            return False

    async def delete_rule(self, rule_id: int, account_id: int) -> bool:
        """Delete a rule"""
        try:
            await self.db.supabase.table('bot_rules').delete().eq(
                'id', rule_id
            ).eq('account_id', account_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting rule: {e}")
            return False 