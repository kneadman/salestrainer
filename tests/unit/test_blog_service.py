from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.blog.models import BlogPost
from app.blog.schemas import BlogPostCreateRequest, BlogPostUpdateRequest
from app.blog.service import BlogConflictError, BlogNotFoundError, BlogService
from app.infrastructure.db import Base, import_model_modules


def _create_session() -> Session:
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    return session_factory()


def _sample_create(**overrides: object) -> BlogPostCreateRequest:
    defaults = {
        "title": "Test Post",
        "excerpt": "Short excerpt",
        "content": "Full content here",
        "author_name": "Author",
        "is_published": False,
    }
    defaults.update(overrides)  # type: ignore[arg-type]
    return BlogPostCreateRequest.model_validate(defaults)


def test_list_published_returns_only_published() -> None:
    session = _create_session()
    service = BlogService(session)

    service.create(_sample_create(title="Draft", is_published=False))
    service.create(_sample_create(title="Published", is_published=True))

    items, total = service.list_published(limit=10, offset=0)
    assert total == 1
    assert items[0].title == "Published"


def test_get_published_by_slug_found() -> None:
    session = _create_session()
    service = BlogService(session)

    service.create(_sample_create(title="Hello", slug="hello", is_published=True))
    dto = service.get_published_by_slug("hello")
    assert dto.title == "Hello"
    assert dto.content == "Full content here"


def test_get_published_by_slug_not_found() -> None:
    session = _create_session()
    service = BlogService(session)

    with raises(BlogNotFoundError):
        service.get_published_by_slug("missing")


def test_create_generates_slug_from_title() -> None:
    session = _create_session()
    service = BlogService(session)

    dto = service.create(_sample_create(title="Привет мир"))
    assert dto.slug == "privet-mir"


def test_create_with_duplicate_slug_raises_conflict() -> None:
    session = _create_session()
    service = BlogService(session)

    service.create(_sample_create(title="First", slug="same"))
    with raises(BlogConflictError):
        service.create(_sample_create(title="Second", slug="same"))


def test_update_sets_published_at_on_first_publish() -> None:
    session = _create_session()
    service = BlogService(session)

    created = service.create(_sample_create(title="Draft", is_published=False))
    assert created.published_at is None

    updated = service.update(created.id, BlogPostUpdateRequest(is_published=True))
    assert updated.is_published is True
    assert updated.published_at is not None


def test_update_slug_unique_check() -> None:
    session = _create_session()
    service = BlogService(session)

    first = service.create(_sample_create(title="First", slug="first"))
    second = service.create(_sample_create(title="Second", slug="second"))

    with raises(BlogConflictError):
        service.update(second.id, BlogPostUpdateRequest(slug="first"))


def test_delete_removes_post() -> None:
    session = _create_session()
    service = BlogService(session)

    created = service.create(_sample_create(title="To delete"))
    service.delete(created.id)

    with raises(BlogNotFoundError):
        service.get_published_by_slug(created.slug)


def test_list_all_search_by_title() -> None:
    session = _create_session()
    service = BlogService(session)

    service.create(_sample_create(title="Alpha", is_published=True))
    service.create(_sample_create(title="Beta", is_published=True))

    items = service.list_all(search="alp")
    assert len(items) == 1
    assert items[0].title == "Alpha"


def test_pagination_offset_and_limit() -> None:
    session = _create_session()
    service = BlogService(session)

    for i in range(5):
        service.create(_sample_create(title=f"Post {i}", is_published=True))

    items, total = service.list_published(limit=2, offset=0)
    assert total == 5
    assert len(items) == 2


# pytest helper re-export to avoid top-level import churn
from pytest import raises
