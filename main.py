import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext

from database import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# Auth utilities
# ======================
ALGORITHM = "HS256"
SECRET_KEY = os.getenv("AUTH_SECRET", "dev-secret-change-me")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ======================
# Models
# ======================
class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ======================
# Helpers
# ======================

def users_col():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    return db["authuser"]  # schema name lowercased


def serialize_user(doc) -> UserOut:
    return UserOut(id=str(doc.get("_id")), email=doc.get("email"), name=doc.get("name"))


def get_current_user(authorization: Optional[str] = Header(None)) -> UserOut:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
        u = users_col().find_one({"_id": db.client.get_default_database().client.get_default_database() if False else None})
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Query by email stored in sub for simplicity
    user_doc = users_col().find_one({"email": sub})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return serialize_user(user_doc)


# ======================
# Basic endpoints
# ======================
@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ======================
# Auth endpoints
# ======================
@app.post("/auth/register", response_model=TokenOut)
def register(body: RegisterBody):
    col = users_col()
    existing = col.find_one({"email": body.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = {
        "email": body.email,
        "password_hash": hash_password(body.password),
        "name": body.name,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "is_active": True,
    }
    col.insert_one(doc)
    user = serialize_user(doc)
    token = create_access_token({"sub": user.email})
    return TokenOut(access_token=token, user=user)


@app.post("/auth/login", response_model=TokenOut)
def login(body: LoginBody):
    col = users_col()
    user_doc = col.find_one({"email": body.email})
    if not user_doc or not verify_password(body.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = serialize_user(user_doc)
    token = create_access_token({"sub": user.email})
    return TokenOut(access_token=token, user=user)


@app.get("/auth/me", response_model=UserOut)
def me(current_user: UserOut = Depends(get_current_user)):
    return current_user


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
