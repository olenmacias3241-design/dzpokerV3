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
    # (Validation logic would be here)
    if get_user_by_username(db, username):
        return None, "用户名已存在"
    
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
    user = get_user_by_username(db, username)
    if not user or not _check_password(user.password_hash, password):
        return None, "用户名或密码错误"
    return user, None

# ... (user_to_profile can be simplified as it now receives an object)
def user_to_profile(user: User):
    if not user: return None
    return {"userId": user.id, "username": user.username, "coinsBalance": user.coins_balance}

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
