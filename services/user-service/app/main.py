import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.logging_config import setup_logging
from shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, setup_metrics
from shared.redis_client import RedisClient

from .auth import create_access_token, decode_token, hash_password, verify_password
from .database import User, get_db
from .schemas import TokenResponse, UserLogin, UserRegister, UserResponse

settings = get_settings()
logger = setup_logging(settings.service_name)
app = FastAPI(title="User Service", version="1.0.0")
setup_metrics(app, settings.service_name)
security = HTTPBearer(auto_error=False)
redis = RedisClient(settings.redis_url)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(settings.service_name, request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(settings.service_name, request.method, request.url.path).observe(time.time() - start)
    return response


@app.get("/health")
def health():
    return {"status": "healthy", "service": settings.service_name}


@app.post("/api/users/register", response_model=UserResponse)
def register(user: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = User(
        email=user.email,
        username=user.username,
        password_hash=hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info("User registered: %s", db_user.id)
    return db_user


@app.post("/api/users/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    redis.set(f"session:{user.id}", token, ttl=3600)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@app.get("/api/users/me", response_model=UserResponse)
def get_me(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
