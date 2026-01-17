from pydantic import BaseModel, EmailStr, field_validator

MAX_BCRYPT_BYTES = 72


def _validate_password_len(pw: str) -> str:
    if pw is None:
        raise ValueError("Password is required")
    if len(pw.encode("utf-8")) > MAX_BCRYPT_BYTES:
        raise ValueError(
            "Password too long (bcrypt limit is 72 bytes)."
        )
    return pw


class RegisterIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_len_ok(cls, v: str) -> str:
        return _validate_password_len(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_len_ok(cls, v: str) -> str:
        return _validate_password_len(v)


class TokenOut(BaseModel):
    access_token: str


class MeOut(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    is_verified: bool
