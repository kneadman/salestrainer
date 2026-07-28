from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints


class BlogPostDTO(BaseModel):
    id: UUID
    slug: str
    title: str
    excerpt: str
    cover_image_url: str | None
    author_name: str
    published_at: datetime | None


class BlogPostDetailDTO(BlogPostDTO):
    content: str


class BlogPostAdminDTO(BlogPostDTO):
    is_published: bool
    created_at: datetime
    updated_at: datetime


class BlogPostListResponse(BaseModel):
    items: list[BlogPostDTO]
    total: int


class BlogPostCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    slug: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ] | None = None
    excerpt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50000)]
    cover_image_url: Annotated[str, StringConstraints(max_length=512)] | None = None
    author_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    is_published: bool = False


class BlogPostUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=300),
    ] | None = None
    slug: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    ] | None = None
    excerpt: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
    ] | None = None
    content: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=50000),
    ] | None = None
    cover_image_url: Annotated[str, StringConstraints(max_length=512)] | None = None
    author_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
    ] | None = None
    is_published: bool | None = None
