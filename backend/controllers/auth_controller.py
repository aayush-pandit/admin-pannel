from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.admin_model import Admin, AuditLog
from schemas.auth_scemas import AdminCreate, AdminLogin
from services.bcrypt_service import BcryptService
from services.jwt_service import JWTService
from services.session_service import SessionService

class AuthController:
    @staticmethod
    def register_admin(db: Session, schema: AdminCreate):
        existing_email = db.query(Admin).filter(Admin.email == schema.email).first()
        existing_user = db.query(Admin).filter(Admin.username == schema.username).first()
        if existing_email or existing_user:
            raise HTTPException(status_code=400, detail="Admin details already exist.")

        hashed = BcryptService.hash_password(schema.password)
        new_admin = Admin(
            username=schema.username,
            email=schema.email,
            hashed_password=hashed,
            role=schema.role
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        # Log Activity
        log = AuditLog(action="Admin Registered", details=f"Created administrative account: {schema.username}", admin_id=new_admin.id)
        db.add(log)
        db.commit()

        return {"message": "Administrative account created successfully"}

    @staticmethod
    def login_admin(db: Session, schema: AdminLogin, ip_address: str, user_agent: str):
        admin = db.query(Admin).filter(Admin.username == schema.username).first()
        if not admin or not BcryptService.verify_password(schema.password, admin.hashed_password):
            log = AuditLog(action="Failed Login Attempt", details=f"Attempted username: {schema.username}", ip_address=ip_address)
            db.add(log)
            db.commit()
            raise HTTPException(status_code=401, detail="Incorrect credentials combination.")

        if not admin.is_active:
            raise HTTPException(status_code=401, detail="Admin status deactivated.")

        access_token = JWTService.create_access_token(data={"sub": str(admin.id), "role": admin.role})
        
        # Save session tracking details
        SessionService.create_session(db, admin.id, access_token, ip_address, user_agent)

        # Audit Activity
        log = AuditLog(action="Admin Logged In", details=f"Admin session active: {admin.username}", admin_id=admin.id, ip_address=ip_address)
        db.add(log)
        db.commit()

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": admin.role,
            "username": admin.username
        }

    @staticmethod
    def logout_admin(db: Session, token: str, admin_id: int):
        SessionService.invalidate_session(db, token)
        log = AuditLog(action="Admin Logged Out", details="System session manually ended.", admin_id=admin_id)
        db.add(log)
        db.commit()
        return {"message": "Successfully logged out from active session."}