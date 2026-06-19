# File: backend/routes/auth_route.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from config.database import get_db
from schemas.auth_scemas import AdminCreate, AdminLogin, ChangePasswordSchema
from controllers.auth_controller import AuthController
from middleware.jwt_auth import get_current_admin
from models.admin_model import Admin

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
def register(schema: AdminCreate, db: Session = Depends(get_db)):
    return AuthController.register_admin(db, schema)

@router.post("/login")
def login(schema: AdminLogin, request: Request, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return AuthController.login_admin(db, schema, ip_address, user_agent)

@router.post("/logout")
def logout(request: Request, current_admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""
    return AuthController.logout_admin(db, token, current_admin.id)

# === NEW CHANGE PASSWORD ROUTE ===
@router.post("/change-password")
def change_password(schema: ChangePasswordSchema, current_admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    return AuthController.change_password(db, schema, current_admin.id)