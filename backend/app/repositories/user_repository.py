from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.models.models import User, UserRole
from backend.app.schemas.auth import UserRegister
from backend.app.security.passwords import get_password_hash


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.strip().lower()).first()

    def create(self, user_in: UserRegister) -> User:
        # Validate role
        role_val = user_in.role if user_in.role in [r.value for r in UserRole] else UserRole.CUSTOMER.value
        db_user = User(
            email=user_in.email.strip().lower(),
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name.strip(),
            role=role_val,
            is_active=True,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def list_all(self, skip: int = 0, limit: int = 50) -> List[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

