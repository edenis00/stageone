import urllib.parse
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.auth import Auth
from app.core.config import settings
from app.schemas.auth import OAuthRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/github")
async def github_login(state: str = None, code_challenge: str = None):
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "user:email",
    }

    if state:
        params["state"] = state
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)

    return RedirectResponse(url)


@router.post("/github/callback")
async def github_callback_cli(
    oauth_request: OAuthRequest,
    db: Session = Depends(get_db),
):
    service = Auth(db)
    return await service.github_callback(
        oauth_request.code, oauth_request.code_verifier, redirect_uri=oauth_request.redirect_uri
    )


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str,
    state: str = None,
    code_verifier: str = None,
    db: Session = Depends(get_db),
):
    if code_verifier:
        verifier = code_verifier
    else:
        verifier = request.cookies.get("pkce_code_verifier")

    if not verifier:
        raise HTTPException(
            status_code=400,
            detail="Missing PKCE code verifier",
        )

    service = Auth(db)

    return await service.github_callback(code, verifier)


@router.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    service = Auth(db)
    return service.refresh_tokens(refresh_token)


@router.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    service = Auth(db)
    return service.logout(refresh_token)
