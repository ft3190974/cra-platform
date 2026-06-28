"""认证：bcrypt 密码 + JWT + RBAC 依赖。"""
from datetime import timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User, now

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# 角色权限等级：数字越大权限越高
ROLE_LEVEL = {"viewer": 1, "auditor": 2, "assessor": 3, "manager": 4, "admin": 5}


def hash_password(p: str) -> str:
    # bcrypt 限制 72 字节，超出截断
    return bcrypt.hashpw(p.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(sub: str) -> str:
    from datetime import datetime, timezone
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": sub, "exp": expire}, settings.secret_key, algorithm="HS256")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "无效的认证凭据")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            raise cred_exc
    except JWTError:
        raise cred_exc
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise cred_exc
    return user


def require_role(min_role: str):
    """依赖工厂：要求当前用户角色不低于 min_role。"""
    def checker(user: User = Depends(get_current_user)) -> User:
        if ROLE_LEVEL.get(user.role, 0) < ROLE_LEVEL.get(min_role, 99):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "权限不足")
        return user
    return checker
