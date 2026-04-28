import secrets
import uuid
import enum
import httpx
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auth import RefreshToken
from app.models.users import User, ROLE


SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_TIME = settings.ACCESS_TOKEN_TIME
REFRESH_TOKEN_TIME = settings.REFRESH_TOKEN_TIME


def create_access_token(data: dict):
    to_encode = data.copy()
    
    # Convert non-serializable objects
    for key, value in to_encode.items():
        if isinstance(value, uuid.UUID):
            to_encode[key] = str(value)
        elif isinstance(value, enum.Enum):
            to_encode[key] = value.value

    to_encode["type"] = "access"
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TIME)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, db: Session):
    token = secrets.token_urlsafe(32)
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_TIME)

    db_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expire,
        is_revoked=False,
    )

    db.add(db_token)
    db.commit()

    return token


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=401,
                detail="Invalid token type",
            )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired",
        )

    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )



class Auth:
    def __init__(self, db: Session):
        self.db = db


    def refresh_tokens(self, refresh_token: str):
        token_in_db = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token == refresh_token)
            .first()
        )

        if not token_in_db or token_in_db.is_revoked:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
            )

        if token_in_db.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=401,
                detail="Refresh token expired",
            )

        token_in_db.is_revoked = True
        self.db.commit()

        access_token = create_access_token(
            {"sub": token_in_db.user_id, "role": token_in_db.user.role}
        )

        new_refresh_token = create_refresh_token(token_in_db.user_id, self.db)

        return {
            "status": "success",
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }

    def logout(self, refresh_token: str):
        token = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token == refresh_token)
            .first()
        )

        if not token:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
            )

        token.is_revoked = True
        self.db.commit()

        return {
            "status": "success",
            "message": "Logout successful",
        }

    async def github_callback(
        self,
        code: str,
        code_verifier: str,
    ):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_REDIRECT_URI,
                    "code_verifier": code_verifier,  # PKCE
                },
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="GitHub token exchange failed",
            )

        token_data = response.json()

        github_access_token = token_data.get("access_token")

        if not github_access_token:
            raise HTTPException(
                status_code=400,
                detail="GitHub authentication failed",
            )

        async with httpx.AsyncClient() as client:
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {github_access_token}"},
            )

        if user_resp.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Failed to fetch GitHub user",
            )

        github_user = user_resp.json()

        github_id = str(github_user["id"])
        username = github_user["login"]
        email = github_user.get("email")
        avatar_url = github_user.get("avatar_url")

        user = (
            self.db.query(User)
            .filter(User.github_id == github_id)
            .first()
        )

        if not user:
            user = User(
                github_id=github_id,
                username=username,
                email=email,
                avatar_url=avatar_url,
                role=ROLE.ANALYST,
                is_active=True,
            )
            self.db.add(user)
        else:
            user.last_login_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(user)


        access_token = create_access_token(
            {"sub": user.id, "role": user.role}
        )

        refresh_token = create_refresh_token(user.id, self.db)

        return {
            "status": "success",
            "access_token": access_token,
            "refresh_token": refresh_token,
        }