from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.errors import not_found
from app.blog.dependencies import get_blog_service
from app.blog.schemas import BlogPostDetailDTO, BlogPostListResponse
from app.blog.service import BlogService, BlogNotFoundError

router = APIRouter(prefix="/api/blog", tags=["blog"])


@router.get("/posts", response_model=BlogPostListResponse)
def list_posts(
    limit: int = Query(default=9, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    service: BlogService = Depends(get_blog_service),
) -> BlogPostListResponse:
    items, total = service.list_published(limit=limit, offset=offset)
    return BlogPostListResponse(items=items, total=total)


@router.get("/posts/{slug}", response_model=BlogPostDetailDTO)
def get_post(
    slug: str,
    service: BlogService = Depends(get_blog_service),
) -> BlogPostDetailDTO:
    try:
        return service.get_published_by_slug(slug)
    except BlogNotFoundError as exc:
        raise not_found(str(exc)) from exc
