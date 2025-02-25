from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from utils.supabase_auth import SupabaseAuth
from utils.database import Database
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

auth = SupabaseAuth()
db = Database()

@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    token: Optional[str] = None,
    error: Optional[str] = None
):
    """Handle Supabase Auth callback"""
    try:
        if error:
            logger.error(f"Auth error: {error}")
            return RedirectResponse(
                url=f"/auth/error?message={error}",
                status_code=302
            )

        if not token:
            raise HTTPException(status_code=400, detail="No token provided")

        # Verify the token and get user
        user = await auth.verify_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get metadata from auth session
        metadata = user.get('user_metadata', {})
        chat_id = metadata.get('chat_id')

        if not chat_id:
            raise HTTPException(status_code=400, detail="No chat ID in metadata")

        # Create or get account
        account = await db.get_or_create_permanent_account(
            user_id=user.id,
            email=user.email,
            chat_id=chat_id
        )

        # Migrate any temporary data
        await db.migrate_temporary_account(chat_id, account['id'])

        # Redirect to dashboard with success message
        return RedirectResponse(
            url="/dashboard?registration=success",
            status_code=302
        )

    except Exception as e:
        logger.error(f"Error in auth callback: {e}")
        return RedirectResponse(
            url="/auth/error?message=registration_failed",
            status_code=302
        ) 