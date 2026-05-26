from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.infrastructure.db import get_db_session
from app.blog.service import BlogService


def get_blog_service(db_session: Session = Depends(get_db_session)) -> BlogService:
    return BlogService(db_session)
