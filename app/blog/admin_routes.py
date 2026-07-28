from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status

from app.blog.dependencies import get_blog_service
from app.blog.schemas import BlogPostAdminDTO, BlogPostCreateRequest, BlogPostUpdateRequest
from app.blog.service import BlogConflictError, BlogNotFoundError, BlogService, BlogValidationError
from app.identity.service import CurrentSession
from app.internal_admin.dependencies import require_internal_admin_session

router = APIRouter(prefix="/api/internal/blog", tags=["internal-admin-blog"])

_MAX_IMAGE_SIZE = 5 * 1024 * 1024
_IMAGE_DEST_DIR = Path("frontend/public/images/blog")


def _handle_blog_error(exc: Exception) -> None:
    if isinstance(exc, BlogNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, BlogConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, BlogValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


@router.get("/posts", response_model=list[BlogPostAdminDTO])
def list_blog_posts(
    search: str | None = None,
    service: BlogService = Depends(get_blog_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[BlogPostAdminDTO]:
    return service.list_all(search=search)


@router.post("/posts", response_model=BlogPostAdminDTO, status_code=status.HTTP_201_CREATED)
def create_blog_post(
    request: BlogPostCreateRequest,
    service: BlogService = Depends(get_blog_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> BlogPostAdminDTO:
    try:
        return service.create(request)
    except Exception as exc:
        _handle_blog_error(exc)


@router.patch("/posts/{post_id}", response_model=BlogPostAdminDTO)
def update_blog_post(
    post_id: UUID,
    request: BlogPostUpdateRequest,
    service: BlogService = Depends(get_blog_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> BlogPostAdminDTO:
    try:
        return service.update(post_id, request)
    except Exception as exc:
        _handle_blog_error(exc)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blog_post(
    post_id: UUID,
    service: BlogService = Depends(get_blog_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> None:
    try:
        service.delete(post_id)
    except Exception as exc:
        _handle_blog_error(exc)


@router.post("/upload-image")
def upload_blog_image(
    image: UploadFile,
    _: CurrentSession = Depends(require_internal_admin_session),
) -> dict[str, str]:
    content = image.file.read()
    if len(content) > _MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File too large. Max 5 MB.")

    mime_type = image.content_type or mimetypes.guess_type(image.filename or "")[0] or ""
    if not mime_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid file type. Only images allowed.")

    ext = mimetypes.guess_extension(mime_type) or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    _IMAGE_DEST_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = _IMAGE_DEST_DIR / filename
    with open(dest_path, "wb") as f:
        f.write(content)

    return {"url": f"/images/blog/{filename}"}
