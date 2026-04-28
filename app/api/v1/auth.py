import secrets
import hashlib
import base64
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.auth import Auth
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["Authentication"])


def generate_pkce():
    code_verifier = secrets.token_urlsafe(64)

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    return code_verifier, code_challenge


@router.get("/github")
async def github_login():
    code_verifier, code_challenge = generate_pkce()

    github_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=read:user user:email"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    response = RedirectResponse(url=github_url)

    response.set_cookie(
        key="pkce_code_verifier",
        value=code_verifier,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return response


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str,
    state: str = None,
    db: Session = Depends(get_db),
):
    code_verifier = request.cookies.get("pkce_code_verifier")

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="Missing PKCE code verifier",
        )

    service = Auth(db)

    return await service.github_callback(code, code_verifier)


@router.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    service = Auth(db)
    return service.refresh_tokens(refresh_token)


@router.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    service = Auth(db)
    return service.logout(refresh_token)