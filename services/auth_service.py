import bcrypt
from database.db import SessionLocal
from database.models import User
from email_validator import validate_email, EmailNotValidError

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def register_user(full_name, email, password):
    db = SessionLocal()
    try:
        # Validate email
        try:
            valid = validate_email(email)
            email = valid.normalized
        except EmailNotValidError as e:
            return False, str(e)
            
        # Check password strength
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
            
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return False, "Email already registered."
            
        hashed_pw = hash_password(password)
        new_user = User(
            full_name=full_name,
            email=email,
            password_hash=hashed_pw
        )
        db.add(new_user)
        db.commit()
        return True, "User registered successfully."
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()

def login_user(email, password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user and check_password(password, user.password_hash):
            return user
        return None
    finally:
        db.close()
