from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, List
import os
import json
from datetime import datetime
from utils.rule_manager import RuleManager
from config.settings import TELEGRAM_TOKEN
from utils.memory_manager import MemoryManager
from config.ai_providers import AIProviderManager
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")
rule_manager = RuleManager()
memory_manager = MemoryManager()
ai_manager = AIProviderManager()
logger = logging.getLogger(__name__)

async def check_telegram_status() -> Dict[str, bool | str]:
    """Check Telegram connection status"""
    try:
        from telegram.ext import Application
        app = (Application.builder()
               .token(TELEGRAM_TOKEN)
               .build())
        await app.initialize()
        await app.bot.get_me()
        return {"status": True, "message": "Connected"}
    except Exception as e:
        return {"status": False, "message": f"Error: {str(e)}"}

async def check_openai_status() -> Dict[str, bool | str]:
    """Check AI provider connection status"""
    try:
        provider_info = ai_manager.get_provider()
        if not provider_info["api_key"]:
            return {"status": False, "message": f"API key not configured for {provider_info['display_name']}"}
            
        if provider_info["name"] == "OpenAI":
            import openai
            client = openai.OpenAI(api_key=provider_info["api_key"])
            models = client.models.list()
            return {"status": True, "message": f"Connected to {provider_info['display_name']}"}
        else:  # Grok
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{provider_info['endpoint']}/models",
                    headers={"Authorization": f"Bearer {provider_info['api_key']}"}
                )
                response.raise_for_status()
                return {"status": True, "message": f"Connected to {provider_info['display_name']}"}
                
    except Exception as e:
        return {"status": False, "message": f"Error connecting to {provider_info['display_name']}: {str(e)}"}

def get_memory_stats() -> Dict[str, int]:
    """Get memory statistics"""
    try:
        with open('memory/short_term.json', 'r') as f:
            short_term = json.load(f)
        with open('memory/history_context.json', 'r') as f:
            context = json.load(f)
        return {
            "message_count": len(short_term),
            "context_count": len(context)
        }
    except Exception:
        return {"message_count": 0, "context_count": 0}

def get_recent_messages(limit: int = 5) -> List[Dict]:
    """Get recent messages"""
    try:
        with open('memory/short_term.json', 'r') as f:
            messages = json.load(f)
        return messages[-limit:]
    except Exception:
        return []

@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    # Get statuses
    telegram_status = await check_telegram_status()
    openai_status = await check_openai_status()
    memory_stats = get_memory_stats()
    
    # Get rules organized by category
    rules = rule_manager.get_rules()
    rules_by_category = {}
    
    # Organize rules by category
    for rule in rules:
        category = rule.category
        if category not in rules_by_category:
            rules_by_category[category] = []
        rules_by_category[category].append(rule)

    # Get current AI provider info
    provider_info = ai_manager.get_provider()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "telegram_status": telegram_status["status"],
            "telegram_status_message": telegram_status["message"],
            "openai_status": openai_status["status"],
            "openai_status_message": openai_status["message"],
            "message_count": memory_stats["message_count"],
            "context_count": memory_stats["context_count"],
            "recent_messages": get_recent_messages(),
            "rules_by_category": rules_by_category,
            "rule_indices": {rule.text: i for i, rule in enumerate(rules)},
            "dashboard_prefix": "/dashboard",
            "active_provider": ai_manager.get_active_provider(),
            "provider_info": provider_info
        }
    )

@router.post("/set_provider")
async def set_provider(provider: str = Form(...)):
    """Set active AI provider"""
    logger.info(f"Attempting to switch to provider: {provider}")
    try:
        if ai_manager.set_active_provider(provider):
            logger.info(f"Successfully switched to {provider}")
            return RedirectResponse(url="/dashboard", status_code=303)
        logger.error(f"Failed to switch to {provider}")
        raise HTTPException(status_code=400, detail="Invalid provider")
    except Exception as e:
        logger.error(f"Error switching provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_config")
async def update_config(api_key: str = Form(...)):
    """Update provider API key"""
    try:
        provider = ai_manager.get_active_provider()
        if ai_manager.update_provider_config(provider, api_key):
            return RedirectResponse(url="/dashboard", status_code=303)
        raise HTTPException(status_code=400, detail="Failed to update configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add_rule")
async def add_rule(
    rule_text: str = Form(...),
    category: str = Form(...),
    priority: int = Form(0)
):
    """Add a new GPT rule"""
    rule_manager.add_rule(rule_text, category, priority)
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/remove_rule")
async def remove_rule(rule_index: int = Form(...)):
    """Remove a GPT rule"""
    rule_manager.remove_rule(rule_index)
    return RedirectResponse(url="/dashboard", status_code=303) 