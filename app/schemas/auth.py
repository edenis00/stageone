from pydantic import BaseModel
from typing import Optional

class OAuthRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: Optional[str] = None