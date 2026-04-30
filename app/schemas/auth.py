from pydantic import BaseModel

class OAuthRequest(BaseModel):
    code: str
    code_verifier: str