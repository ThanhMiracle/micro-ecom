import os
import time
import hashlib
import base64

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .db import Base, engine, SessionLocal, init_schema, set_search_path
from .models import User
from .schemas import RegisterIn, LoginIn, TokenOut, MeOut
from .email_tokens import make_verify_token, decode_verify_token
from shared.events import publish
from shared.security import require_user


# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
JWT_SECRET = os.environ["JWT_SECRET"]
ALGO = "HS256"

# IMPORTANT: Set this to http://localhost:3000 in docker-compose for nginx web
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hard limit just to prevent abuse (not bcrypt-related)
MAX_PASSWORD_BYTES = 4096

# Access token lifetime (seconds)
ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_TTL", str(60 * 60 * 24)))  # 24h


# -------------------------------------------------------------------
# Password helpers
# -------------------------------------------------------------------
def _validate_password(pw: str) -> None:
    if not pw:
        raise HTTPException(status_code=400, detail="Password is required")

    size = len(pw.encode("utf-8"))
    if size > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Password too long (max {MAX_PASSWORD_BYTES} bytes)",
        )


def _normalize_password(pw: str) -> str:
    """
    Pre-hash password using SHA-256 → base64
    Output is always 44 ASCII chars (safe for bcrypt).
    """
    digest = hashlib.sha256(pw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii")


def hash_password(pw: str) -> str:
    _validate_password(pw)
    return pwd.hash(_normalize_password(pw))


def verify_password(pw: str, pw_hash: str) -> bool:
    _validate_password(pw)
    return pwd.verify(_normalize_password(pw), pw_hash)


# -------------------------------------------------------------------
# App
# -------------------------------------------------------------------
app = FastAPI(title="auth-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# Admin seed
# -------------------------------------------------------------------
def seed_admin(db: Session):
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        return

    if db.query(User).filter(User.email == ADMIN_EMAIL).first():
        return

    try:
        pw_hash = hash_password(ADMIN_PASSWORD)
    except HTTPException as e:
        print("ADMIN seed skipped:", e.detail)
        return

    admin = User(
        email=ADMIN_EMAIL,
        password_hash=pw_hash,
        is_admin=True,
        is_verified=True,
    )
    db.add(admin)
    db.commit()


@app.on_event("startup")
def startup():
    init_schema()
    set_search_path()
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        seed_admin(db)


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.post("/auth/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        is_admin=False,
        is_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = make_verify_token(user.id, user.email)

    # Frontend route receives token, then frontend should call backend /auth/verify
    verify_url = f"{FRONTEND_BASE_URL}/verify?token={token}"

    # Publish event for notify-service (Mailhog)
    if RABBITMQ_URL:
        publish(
            RABBITMQ_URL,
            "user.registered",
            {"email": user.email, "verify_url": verify_url},
        )

    return {"ok": True, "message": "Registered. Please verify your email."}


@app.get("/auth/verify")
def verify_get(token: str, db: Session = Depends(get_db)):
    return _verify_token(token, db)


@app.post("/auth/verify")
def verify_post(body: dict, db: Session = Depends(get_db)):
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")
    return _verify_token(token, db)


def _verify_token(token: str, db: Session):
    try:
        data = decode_verify_token(token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = (
        db.query(User)
        .filter(User.id == int(data["sub"]), User.email == data["email"])
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.commit()
    return {"ok": True}


@app.post("/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin,
            "iat": now,
            "exp": now + ACCESS_TOKEN_TTL,
            "typ": "access",
        },
        JWT_SECRET,
        algorithm=ALGO,
    )
    return {"access_token": token}


@app.get("/auth/me", response_model=MeOut)
def me(claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == int(claims["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return MeOut(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        is_verified=user.is_verified,
    )

@app.get("/health")
def health():
    return {"ok": True}