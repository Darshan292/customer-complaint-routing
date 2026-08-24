from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.schemas.auth_schema import LoginRequest
from app.services.auth_service import login_user

router = APIRouter(tags=["Authentication"])

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    user = login_user(
        request.email,
        request.password,
        db,
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    role = user.role

    # Normalize the legacy "user" role to the
    # enterprise application's canonical role.
    if role == "user":
        role = "customer"

    if role not in {
        "admin",
        "agent",
        "customer",
    }:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Unsupported account role: {role}"
            ),
        )

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role,
        "team": getattr(
            user,
            "team",
            None,
        ),
    }