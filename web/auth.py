from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from utils.database import Database
from utils.registration_handler import RegistrationHandler
from datetime import datetime, timedelta
from utils.auth_utils import create_access_token, get_current_user
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.params import Form
from fastapi.templating import Jinja2Templates
from typing import Optional
import secrets

router = APIRouter()

class RegistrationData(BaseModel):
    token: str
    password: str
    name: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    email: str
    password: str

templates = Jinja2Templates(directory="templates")

@router.post("/register/verify")
async def verify_registration(data: RegistrationData):
    try:
        # Get registration info
        reg_info = registration_handler.pending_registrations.get(data.token)
        if not reg_info or datetime.now() > reg_info['expires_at']:
            raise HTTPException(status_code=400, message="Invalid or expired token")

        # Create permanent account
        account = await db.create_permanent_account(
            name=data.name,
            email=reg_info['email'],
            password=data.password,
            chat_id=reg_info['chat_id']
        )

        # Migrate temporary data
        await db.migrate_temporary_account(reg_info['chat_id'], account['id'])

        # Send welcome email
        await email_service.send_welcome_email(reg_info['email'], data.name)

        # Clean up
        del registration_handler.pending_registrations[data.token]

        return {"status": "success", "account_id": account['id']}

    except Exception as e:
        logger.error(f"Error in registration verification: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Database = Depends()):
    user = await db.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user["id"])},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/signup")
async def signup_page(
    request: Request,
    chat_id: int,
    error: Optional[str] = None
):
    return templates.TemplateResponse(
        "auth/signup.html",
        {
            "request": request,
            "chat_id": chat_id,
            "error": error
        }
    )

@router.post("/signup")
async def handle_signup(
    request: Request,
    email: str = Form(...),
    chat_id: int = Form(...)
):
    try:
        # Send magic link via Supabase Auth
        await supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {
                "data": {
                    "chat_id": chat_id,
                    "redirect_to": f"/auth/verify"
                }
            }
        })
        
        return templates.TemplateResponse(
            "auth/check_email.html",
            {"request": request}
        )
        
    except Exception as e:
        logger.error(f"Error in signup: {e}")
        return RedirectResponse(
            url=f"/auth/signup?chat_id={chat_id}&error=signup_failed",
            status_code=303
        ) 