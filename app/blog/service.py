from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.blog.models import BlogPost
from app.blog.schemas import (
    BlogPostAdminDTO,
    BlogPostCreateRequest,
    BlogPostDTO,
    BlogPostDetailDTO,
    BlogPostUpdateRequest,
)


class BlogServiceError(Exception):
    pass


class BlogNotFoundError(BlogServiceError):
    pass


class BlogConflictError(BlogServiceError):
    pass


class BlogValidationError(BlogServiceError):
    pass


_TRANSLIT_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _transliterate(text: str) -> str:
    result = []
    for ch in text.lower():
        if ch in _TRANSLIT_MAP:
            result.append(_TRANSLIT_MAP[ch])
        elif ch.isalnum():
            result.append(ch)
        else:
            result.append("-")
    return "".join(result)


def _generate_slug(title: str) -> str:
    raw = _transliterate(title)
    # collapse multiple hyphens
    raw = re.sub(r"-+", "-", raw)
    raw = raw.strip("-")
    # truncate to reasonable length
    if len(raw) > 80:
        raw = raw[:80].rsplit("-", 1)[0]
    return raw or "post"


class BlogService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_published(self, limit: int, offset: int) -> tuple[list[BlogPostDTO], int]:
        stmt_count = select(func.count()).select_from(BlogPost).where(BlogPost.is_published.is_(True))
        total = self._session.scalar(stmt_count) or 0

        stmt = (
            select(BlogPost)
            .where(BlogPost.is_published.is_(True))
            .order_by(desc(BlogPost.published_at))
            .offset(offset)
            .limit(limit)
        )
        rows = list(self._session.scalars(stmt))
        return [self._to_dto(row) for row in rows], total

    def get_published_by_slug(self, slug: str) -> BlogPostDetailDTO:
        row = self._session.scalar(
            select(BlogPost).where(BlogPost.slug == slug, BlogPost.is_published.is_(True))
        )
        if row is None:
            raise BlogNotFoundError(f"Blog post with slug '{slug}' not found.")
        return self._to_detail_dto(row)

    def list_all(self, search: str | None = None) -> list[BlogPostAdminDTO]:
        stmt = select(BlogPost).order_by(desc(BlogPost.updated_at))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    BlogPost.title.ilike(pattern),
                    BlogPost.slug.ilike(pattern),
                    BlogPost.content.ilike(pattern),
                )
            )
        rows = list(self._session.scalars(stmt))
        return [self._to_admin_dto(row) for row in rows]

    def create(self, request: BlogPostCreateRequest) -> BlogPostAdminDTO:
        slug = request.slug or _generate_slug(request.title)
        if self._slug_exists(slug):
            raise BlogConflictError(f"Slug '{slug}' already exists.")

        published_at: datetime | None = None
        if request.is_published:
            published_at = datetime.now(timezone.utc)

        post = BlogPost(
            title=request.title,
            slug=slug,
            excerpt=request.excerpt,
            content=request.content,
            cover_image_url=request.cover_image_url,
            author_name=request.author_name,
            is_published=request.is_published,
            published_at=published_at,
        )
        self._session.add(post)
        self._commit_or_conflict()
        self._session.refresh(post)
        return self._to_admin_dto(post)

    def update(self, post_id: UUID, request: BlogPostUpdateRequest) -> BlogPostAdminDTO:
        post = self._session.get(BlogPost, post_id)
        if post is None:
            raise BlogNotFoundError(f"Blog post with id '{post_id}' not found.")

        updates = request.model_dump(exclude_unset=True)

        new_slug = updates.pop("slug", None)
        if new_slug is not None and new_slug != post.slug:
            if self._slug_exists(new_slug, exclude_id=post_id):
                raise BlogConflictError(f"Slug '{new_slug}' already exists.")
            post.slug = new_slug

        new_is_published = updates.pop("is_published", None)
        if new_is_published is not None:
            if not post.is_published and new_is_published:
                post.published_at = datetime.now(timezone.utc)
            post.is_published = new_is_published

        for key, value in updates.items():
            setattr(post, key, value)

        self._commit_or_conflict()
        self._session.refresh(post)
        return self._to_admin_dto(post)

    def delete(self, post_id: UUID) -> None:
        post = self._session.get(BlogPost, post_id)
        if post is None:
            raise BlogNotFoundError(f"Blog post with id '{post_id}' not found.")
        self._session.delete(post)
        self._session.commit()

    def _slug_exists(self, slug: str, exclude_id: UUID | None = None) -> bool:
        stmt = select(BlogPost).where(BlogPost.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(BlogPost.id != exclude_id)
        return self._session.scalar(stmt) is not None

    def _commit_or_conflict(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise BlogConflictError("Slug already exists.") from exc

    def _to_dto(self, post: BlogPost) -> BlogPostDTO:
        return BlogPostDTO(
            id=post.id,
            slug=post.slug,
            title=post.title,
            excerpt=post.excerpt,
            cover_image_url=post.cover_image_url,
            author_name=post.author_name,
            published_at=post.published_at,
        )

    def _to_detail_dto(self, post: BlogPost) -> BlogPostDetailDTO:
        return BlogPostDetailDTO(
            id=post.id,
            slug=post.slug,
            title=post.title,
            excerpt=post.excerpt,
            cover_image_url=post.cover_image_url,
            author_name=post.author_name,
            published_at=post.published_at,
            content=post.content,
        )

    def _to_admin_dto(self, post: BlogPost) -> BlogPostAdminDTO:
        return BlogPostAdminDTO(
            id=post.id,
            slug=post.slug,
            title=post.title,
            excerpt=post.excerpt,
            cover_image_url=post.cover_image_url,
            author_name=post.author_name,
            published_at=post.published_at,
            is_published=post.is_published,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
