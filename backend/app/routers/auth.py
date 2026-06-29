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
from ..schemas import Token, UserCreate, UserOut, UserUpdate, UserPasswordReset

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["users"])


@auth_router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db),
          _rate: None = Depends(login_limiter)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已禁用")
    log_action(db, user, "LOGIN", "auth", user.id, {})
    return Token(access_token=create_access_token(user.username))


@auth_router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# ═══════════════════ 用户管理 CRUD ═══════════════════

@users_router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_role("manager"))):
    return db.query(User).order_by(User.id).all()


@users_router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db),
             _: User = Depends(require_role("manager"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    return u


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


@users_router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db),
                admin: User = Depends(require_role("admin"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    # 不允许修改自己的角色（防止把自己降权）
    if u.id == admin.id and payload.role is not None and payload.role != admin.role:
        raise HTTPException(400, "不能修改自己的角色")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    db.commit(); db.refresh(u)
    log_action(db, admin, "UPDATE", "user", user_id, {k: v for k, v in payload.model_dump(exclude_unset=True).items()})
    return u


@users_router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),
                admin: User = Depends(require_role("admin"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    if u.id == admin.id:
        raise HTTPException(400, "不能删除自己的账号")
    db.delete(u); db.commit()
    log_action(db, admin, "DELETE", "user", user_id, {"username": u.username})
    return {"ok": True}


@users_router.put("/{user_id}/reset-password")
def reset_user_password(user_id: int, payload: UserPasswordReset,
                         db: Session = Depends(get_db),
                         admin: User = Depends(require_role("admin"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    if len(payload.new_password) < 6:
        raise HTTPException(400, "密码至少6位")
    u.hashed_password = hash_password(payload.new_password)
    db.commit()
    log_action(db, admin, "UPDATE", "user", user_id, {"action": "reset_password"})
    return {"ok": True}


@users_router.put("/{user_id}/toggle-active", response_model=UserOut)
def toggle_user_active(user_id: int, db: Session = Depends(get_db),
                       admin: User = Depends(require_role("admin"))):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    if u.id == admin.id:
        raise HTTPException(400, "不能禁用自己的账号")
    u.is_active = not u.is_active
    db.commit(); db.refresh(u)
    log_action(db, admin, "UPDATE", "user", user_id, {"is_active": u.is_active})
    return u
