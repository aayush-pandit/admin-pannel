# File: backend/schemas/auth_scemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class AdminCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "admin"

class AdminLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

# === YEH CLASS MISSING THI, AB ADD HO GAYI HAI ===
class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str