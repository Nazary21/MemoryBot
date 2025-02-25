from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from config.database import init_supabase
import logging

logger = logging.getLogger(__name__)

# For FastAPI auth middleware
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Verify Supabase session and get current user"""
    try:
        supabase = init_supabase()
        user = await supabase.auth.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        ) 