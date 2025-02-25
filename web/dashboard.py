from fastapi import APIRouter, Request, Form, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Dict, List
import os
import json
from datetime import datetime, timedelta
from utils.rule_manager import RuleManager
from config.settings import TELEGRAM_TOKEN
from utils.memory_manager import MemoryManager
from config.ai_providers import AIProviderManager
import logging
import secrets
from utils.auth_utils import get_current_user
from utils.database import Database
from utils.ai_response import AIResponseHandler

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Initialize database and managers
db = Database()
rule_manager = RuleManager(db)
memory_manager = MemoryManager(account_id=1, db=db)
ai_manager = AIProviderManager()
logger = logging.getLogger(__name__)

# Initialize HTTP Basic Auth
security = HTTPBasic(auto_error=False)

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic Auth credentials"""
    try:
        # Get configured credentials
        configured_username = os.getenv("DASHBOARD_USERNAME")
        configured_password = os.getenv("DASHBOARD_PASSWORD")
        
        # Use default credentials if either is not configured
        using_defaults = False
        if not configured_username or not configured_password:
            using_defaults = True
            configured_username = "admin"
            configured_password = "pykhbrain"
            logger.info("Using default credentials (admin/pykhbrain)")
        
        # If no credentials provided, prompt for authentication
        if not credentials:
            logger.debug("No credentials provided, requesting authentication")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please provide credentials",
                headers={"WWW-Authenticate": 'Basic realm="PykhBrain Dashboard"'},
            )
        
        # Compare credentials using constant-time comparison
        try:
            is_username_correct = secrets.compare_digest(
                credentials.username.encode("utf-8"), 
                configured_username.encode("utf-8")
            )
            is_password_correct = secrets.compare_digest(
                credentials.password.encode("utf-8"), 
                configured_password.encode("utf-8")
            )
        except Exception as e:
            logger.error(f"Error comparing credentials: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials format",
                headers={"WWW-Authenticate": 'Basic realm="PykhBrain Dashboard"'},
            )
        
        if not (is_username_correct and is_password_correct):
            logger.warning(f"Invalid credentials attempt for user: {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": 'Basic realm="PykhBrain Dashboard"'},
            )
        
        logger.info(f"Successful login for user: {credentials.username}{' (using default credentials)' if using_defaults else ''}")
        return {"username": credentials.username, "using_defaults": using_defaults}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )

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
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return {"message_count": 0, "context_count": 0}

def get_recent_messages(limit: int = 5) -> List[Dict]:
    """Get recent messages"""
    try:
        with open('memory/short_term.json', 'r') as f:
            messages = json.load(f)
        return messages[-limit:]
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        return []

@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, auth_info: dict = Depends(verify_credentials)):
    """Dashboard main view with authentication"""
    try:
        # Get statuses
        telegram_status = await check_telegram_status()
        openai_status = await check_openai_status()
        memory_stats = get_memory_stats()
        
        # Get rules organized by category
        try:
            # Use default account_id=1
            rules = await rule_manager.get_rules(account_id=1)
        except Exception as e:
            logger.error(f"Error getting rules: {e}")
            rules = []
            
        rules_by_category = {}
        
        # Organize rules by category
        for rule in rules:
            # Default category if not available
            category = getattr(rule, 'category', 'General')
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
                "provider_info": provider_info,
                "username": auth_info["username"],
                "using_default_auth": auth_info["using_defaults"]
            }
        )
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/set_provider")
async def set_provider(provider: str = Form(...), username: str = Depends(verify_credentials)):
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
async def update_config(api_key: str = Form(...), username: str = Depends(verify_credentials)):
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
    priority: int = Form(0),
    username: str = Depends(verify_credentials)
):
    """Add a new GPT rule"""
    rule_manager.add_rule(rule_text, category, priority)
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/remove_rule")
async def remove_rule(
    rule_index: int = Form(...),
    username: str = Depends(verify_credentials)
):
    """Remove a GPT rule"""
    rule_manager.remove_rule(rule_index)
    return RedirectResponse(url="/dashboard", status_code=303)

@router.get("/overview", response_class=HTMLResponse)
async def dashboard_overview(
    request: Request,
    current_user = Depends(get_current_user),
    db: Database = Depends()
):
    """Dashboard overview page"""
    try:
        # Get account info
        account = await db.get_account(current_user['account_id'])
        
        # Get basic stats
        memory_stats = await db.get_memory_stats(account['id'])
        recent_messages = await db.get_memory_by_type(account['id'], 'short_term', limit=5)
        
        return templates.TemplateResponse(
            "dashboard/overview.html",
            {
                "request": request,
                "user": current_user,
                "account": account,
                "memory_stats": memory_stats,
                "recent_messages": recent_messages,
                "active_page": "overview"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory", response_class=HTMLResponse)
async def memory_view(
    request: Request,
    current_user = Depends(get_current_user),
    db: Database = Depends()
):
    """Memory management page"""
    try:
        account_id = current_user['account_id']
        
        memory_stats = await db.get_memory_stats(account_id)
        recent_messages = await db.get_memory_by_type(account_id, 'short_term', limit=20)
        history_context = await db.get_history_context(account_id)
        
        return templates.TemplateResponse(
            "dashboard/memory.html",
            {
                "request": request,
                "user": current_user,
                "memory_stats": memory_stats,
                "recent_messages": recent_messages,
                "history_context": history_context,
                "active_page": "memory"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin", response_class=HTMLResponse)
async def admin_view(
    request: Request,
    current_user = Depends(get_current_user),
    db: Database = Depends()
):
    """Admin dashboard"""
    if not current_user['is_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    try:
        # Get system-wide stats
        accounts = await db.get_all_accounts()
        total_messages = await db.get_total_message_count()
        active_users = await db.get_active_users_count(last_days=7)
        
        return templates.TemplateResponse(
            "dashboard/admin.html",
            {
                "request": request,
                "user": current_user,
                "accounts": accounts,
                "total_messages": total_messages,
                "active_users": active_users,
                "active_page": "admin"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings", response_class=HTMLResponse)
async def settings_view(
    request: Request,
    current_user = Depends(get_current_user),
    db: Database = Depends()
):
    """Settings page view"""
    try:
        account_id = current_user['account_id']
        
        # Get current AI settings
        ai_handler = AIResponseHandler(db)
        current_settings = await ai_handler.get_account_model_settings(account_id)
        available_models = ai_handler.get_available_models()
        
        # Get usage statistics
        usage_stats = {
            "current_period": await db.get_usage_stats(account_id, period="current"),
            "previous_period": await db.get_usage_stats(account_id, period="previous")
        }
        
        return templates.TemplateResponse(
            "dashboard/settings.html",
            {
                "request": request,
                "user": current_user,
                "current_settings": current_settings,
                "available_models": available_models,
                "usage_stats": usage_stats,
                "active_page": "settings"
            }
        )
    except Exception as e:
        logger.error(f"Error in settings view: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_model_settings")
async def update_model_settings(
    request: Request,
    model_name: str = Form(...),
    temperature: float = Form(...),
    max_tokens: int = Form(...),
    current_user = Depends(get_current_user),
    db: Database = Depends()
):
    """Update AI model settings"""
    try:
        # Validate inputs
        if not (0 <= temperature <= 1):
            raise HTTPException(status_code=400, detail="Temperature must be between 0 and 1")
            
        if not (100 <= max_tokens <= 3000):
            raise HTTPException(status_code=400, detail="Max tokens must be between 100 and 3000")
            
        ai_handler = AIResponseHandler(db)
        available_models = ai_handler.get_available_models()
        
        if model_name not in available_models:
            raise HTTPException(status_code=400, detail="Invalid model selected")
        
        # Update settings
        settings = {
            "model": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        success = await ai_handler.update_model_settings(current_user['account_id'], settings)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update settings")
            
        return RedirectResponse(
            url="/dashboard/settings",
            status_code=303
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating model settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 