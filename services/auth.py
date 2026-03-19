# dzpokerV3/services/auth.py
import re
import time
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import Session
from database import User, SessionLocal
import config
import jwt

# (Validation functions remain the same)
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9]{4,16}$")
PASSWORD_MIN, PASSWORD_MAX = 6, 20
def _hash_password(p): return generate_password_hash(p, method="pbkdf2:sha256")
def _check_password(h, p): return check_password_hash(h, p)
# ... (validation helpers)

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username, password, email=None):
    if not username or not username.strip():
        return None, "用户名不能为空"
    username = username.strip()
    if not USERNAME_PATTERN.match(username):
        return None, "用户名为 4–16 位字母或数字"
    if not password or len(password) < PASSWORD_MIN or len(password) > PASSWORD_MAX:
        return None, f"密码长度为 {PASSWORD_MIN}–{PASSWORD_MAX} 位"
    if get_user_by_username(db, username):
        return None, "用户名已存在"
    if email and email.strip():
        email = email.strip()
    hashed_password = _hash_password(password)
    new_user = User(
        username=username,
        password_hash=hashed_password,
        email=email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user, None

def verify_user(db: Session, username, password):
    if not username or not password:
        return None, "用户名或密码错误"
    user = get_user_by_username(db, username)
    if not user:
        return None, "用户名或密码错误"
    if not user.password_hash:
        return None, "该账号未设置密码，请使用钱包登录"
    if not _check_password(user.password_hash, password):
        return None, "用户名或密码错误"
    return user, None

def user_to_profile(user: User, stats: dict = None):
    if not user:
        return None
    out = {"userId": user.id, "username": user.username, "coinsBalance": user.coins_balance}
    if stats:
        out["stats"] = stats
    return out


def get_user_stats(db: Session, user_id: int):
    """从 hand_participants 汇总用户的局数、胜率、最大单局盈利。"""
    try:
        from database import HandParticipant
        from sqlalchemy import func
        total = db.query(func.count(HandParticipant.hand_id)).filter(HandParticipant.user_id == user_id).scalar() or 0
        wins = db.query(func.count(HandParticipant.hand_id)).filter(
            HandParticipant.user_id == user_id,
            HandParticipant.win_amount > 0,
        ).scalar() or 0
        biggest = db.query(func.max(HandParticipant.win_amount)).filter(
            HandParticipant.user_id == user_id,
        ).scalar() or 0
        return {
            "totalHandsPlayed": total,
            "winRate": round(100.0 * wins / total, 1) if total else 0,
            "biggestPotWon": int(biggest),
        }
    except Exception:
        return {"totalHandsPlayed": 0, "winRate": 0, "biggestPotWon": 0}

def encode_jwt(user_id, expires_seconds=7 * 24 * 3600):
    payload = {"user_id": int(user_id), "exp": time.time() + expires_seconds}
    return jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")

def decode_jwt(token):
    if not token: return None
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None

# The API endpoints in app.py will need to be updated to pass the db session.
