from sqlalchemy.orm import Session
from models.session_model import SessionModel

class SessionService:
    @staticmethod
    def create_session(db: Session, admin_id: int, token: str, ip_address: str, user_agent: str):
        db_session = SessionModel(
            admin_id=admin_id,
            token=token,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session

    @staticmethod
    def invalidate_session(db: Session, token: str):
        db_session = db.query(SessionModel).filter(SessionModel.token == token).first()
        if db_session:
            db_session.is_active = False
            db.commit()
            return True
        return False

    @staticmethod
    def is_session_active(db: Session, token: str) -> bool:
        db_session = db.query(SessionModel).filter(SessionModel.token == token).first()
        return db_session is not None and db_session.is_active