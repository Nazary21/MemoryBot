import json
import os
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

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
    def __init__(self, rules_file: str = "memory/rules.json"):
        self.rules_file = rules_file
        self._ensure_rules_file_exists()

    def _ensure_rules_file_exists(self):
        """Ensure the rules file exists, create if it doesn't"""
        os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
        if not os.path.exists(self.rules_file):
            default_rules = [
                GPTRule("Always respond in the same language as the user's message", "Language", 1),
                GPTRule("Remember and use people's names when they introduce themselves", "Personalization", 1),
                GPTRule("Be helpful and friendly while maintaining a professional tone", "Tone", 1),
                GPTRule("Share conversation history and context openly when asked", "Memory", 1),
                GPTRule("Keep track of important information shared in conversation", "Memory", 0),
                GPTRule("Use emojis appropriately to make responses more engaging", "Tone", 0)
            ]
            with open(self.rules_file, 'w') as f:
                json.dump([rule.to_dict() for rule in default_rules], f, indent=2)
            logger.info("Created rules file with default rules")

    def get_rules(self) -> List[GPTRule]:
        """Get all rules from the file"""
        try:
            with open(self.rules_file, 'r') as f:
                rules_data = json.load(f)
                return [GPTRule.from_dict(rule_data) for rule_data in rules_data]
        except Exception as e:
            logger.error(f"Error reading rules: {e}")
            return []

    def add_rule(self, rule: str, category: str = "General", priority: int = 0) -> bool:
        """Add a new rule with category and priority"""
        try:
            rules = self.get_rules()
            new_rule = GPTRule(text=rule, category=category, priority=priority)
            rules.append(new_rule)
            with open(self.rules_file, 'w') as f:
                json.dump([r.to_dict() for r in rules], f, indent=2)
            logger.info(f"Added new rule in category {category}")
            return True
        except Exception as e:
            logger.error(f"Error adding rule: {e}")
            return False

    def remove_rule(self, index: int) -> bool:
        """Remove a rule by its index"""
        try:
            rules = self.get_rules()
            if 0 <= index < len(rules):
                removed_rule = rules.pop(index)
                with open(self.rules_file, 'w') as f:
                    json.dump([r.to_dict() for r in rules], f, indent=2)
                logger.info(f"Removed rule: {removed_rule.text}")
                return True
            else:
                logger.error(f"Invalid rule index: {index}")
                return False
        except Exception as e:
            logger.error(f"Error removing rule: {e}")
            return False

    def get_formatted_rules(self) -> str:
        """Get rules formatted for GPT context"""
        rules = self.get_rules()
        if not rules:
            return "No specific rules set."
            
        # Sort rules by priority (1 = core rules, 0 = optional rules)
        core_rules = [r.text for r in rules if r.priority == 1]
        optional_rules = [r.text for r in rules if r.priority == 0]
        
        formatted = "Rules to follow:\n"
        
        if core_rules:
            formatted += "\nCore rules (must follow):\n"
            formatted += "\n".join(f"- {rule}" for rule in core_rules)
            
        if optional_rules:
            formatted += "\nOptional rules (when applicable):\n"
            formatted += "\n".join(f"- {rule}" for rule in optional_rules)
            
        return formatted 