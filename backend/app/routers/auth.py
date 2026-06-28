"""认证 + 用户管理路由。"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..audit import log_action
from ..auth import (create_access_token, get_current_user, hash_password,
                   require_role, verify_password)
from ..database import get_db
from ..models import User
from ..rate_limit import login_limiter
from ..schemas import Token, UserCreate, UserOut

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["users"])


@auth_router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db),
          _rate: None = Depends(login_limiter)):
    user = db.query(User).filter(User.username == form.username).first()
    # 统一错误提示，防止用户名枚举
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已禁用")
    log_action(db, user, "LOGIN", "auth", user.id, {})
    return Token(access_token=create_access_token(user.username))


@auth_router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@users_router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_role("manager"))):
    return db.query(User).all()


@users_router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db),
                admin: User = Depends(require_role("admin"))):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, "用户名已存在")
    u = User(username=payload.username, email=payload.email, full_name=payload.full_name,
             role=payload.role, dept_id=payload.dept_id,
             hashed_password=hash_password(payload.password))
    db.add(u); db.commit(); db.refresh(u)
    log_action(db, admin, "CREATE", "user", u.id, {"username": u.username})
    return u
