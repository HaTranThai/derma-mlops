from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.repositories import user_repository
from app.services import auth_service

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest):
    user = user_repository.get_user(payload.username)
    if user is None or not auth_service.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")
    token = auth_service.create_access_token(user["username"], user["role"])
    return {"access_token": token, "username": user["username"], "role": user["role"]}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user
