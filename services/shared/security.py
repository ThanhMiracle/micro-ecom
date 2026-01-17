import os
from fastapi import Header, HTTPException
from jose import jwt

JWT_SECRET = os.environ["JWT_SECRET"]
ALGO = "HS256"

def require_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    except Exception:
        raise HTTPException(401, "Invalid token")

def require_admin(claims: dict) -> dict:
    if not claims.get("is_admin"):
        raise HTTPException(403, "Admin only")
    return claims
