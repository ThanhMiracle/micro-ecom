import os, time
from jose import jwt

JWT_SECRET = os.environ["JWT_SECRET"]
ALGO = "HS256"

def make_verify_token(user_id: int, email: str, ttl_seconds: int = 3600) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": str(user_id), "email": email, "iat": now, "exp": now + ttl_seconds, "typ": "verify"},
        JWT_SECRET,
        algorithm=ALGO,
    )

def decode_verify_token(token: str) -> dict:
    data = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    if data.get("typ") != "verify":
        raise ValueError("Invalid token type")
    return data
