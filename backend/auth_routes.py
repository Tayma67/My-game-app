"""Authentication API routes."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
from bson import ObjectId

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    make_get_current_user,
)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=60)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def build_auth_router(db):
    router = APIRouter(prefix="/api/auth", tags=["auth"])
    get_current_user = make_get_current_user(db)

    @router.post("/register")
    async def register(body: RegisterIn):
        email = body.email.lower().strip()
        existing = await db.users.find_one({"email": email})
        if existing:
            raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı")
        doc = {
            "email": email,
            "password_hash": hash_password(body.password),
            "name": body.name.strip(),
            "role": "player",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        res = await db.users.insert_one(doc)
        uid = str(res.inserted_id)
        token = create_access_token(uid, email)
        return {
            "token": token,
            "user": {"id": uid, "email": email, "name": doc["name"]},
        }

    @router.post("/login")
    async def login(body: LoginIn):
        email = body.email.lower().strip()
        user = await db.users.find_one({"email": email})
        if not user or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
        uid = str(user["_id"])
        token = create_access_token(uid, email)
        return {
            "token": token,
            "user": {"id": uid, "email": email, "name": user.get("name", "")},
        }

    @router.get("/me")
    async def me(user: dict = Depends(get_current_user)):
        return {
            "id": user["_id"],
            "email": user["email"],
            "name": user.get("name", ""),
        }

    return router
