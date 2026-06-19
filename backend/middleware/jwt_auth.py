from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from config.database import get_db
from services.jwt_service import JWTService
from services.session_service import SessionService
from models.admin_model import Admin

security = HTTPBearer()

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    
    # Session state validation
    if not SessionService.is_session_active(db, token):
         raise HTTPException(status_code=401, detail="Session expired or deactivated.")

    payload = JWTService.verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token details")
    
    admin_id = payload.get("sub")
    if admin_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    admin = db.query(Admin).filter(Admin.id == int(admin_id)).first()
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=401, detail="Authorized administrator block status detected.")
    
    return admin