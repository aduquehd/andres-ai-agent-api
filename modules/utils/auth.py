import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config import settings


security = HTTPBasic()


def get_current_username(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = settings.admin_user.encode("utf-8")
    is_correct_username = secrets.compare_digest(current_username_bytes, correct_username_bytes)

    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = settings.admin_password.encode("utf8")
    is_correct_password = secrets.compare_digest(current_password_bytes, correct_password_bytes)

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def get_user_id_from_auth_header(request: Request) -> str:
    """
    Extract user ID from Authorization header with format 'User-Id {uuid}'.

    This is a FastAPI dependency that can be used to authenticate users
    based on their client-generated UUID sent in the Authorization header.

    Args:
        request: FastAPI Request object containing headers

    Returns:
        str: The user ID extracted from the Authorization header

    Raises:
        HTTPException: If Authorization header is missing, malformed, or empty
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "User-Id"},
        )

    if not auth_header.startswith("User-Id "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with 'User-Id '",
            headers={"WWW-Authenticate": "User-Id"},
        )

    user_id = auth_header.replace("User-Id ", "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID is required in Authorization header",
            headers={"WWW-Authenticate": "User-Id"},
        )

    return user_id
