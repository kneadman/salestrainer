from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import create_app
from app.identity.dependencies import get_db_session
from app.identity.models import User
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, import_model_modules
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository


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


def _create_client(session: Session) -> TestClient:
    app = create_app(
        settings=Settings(
            auth_cookie_secure=False,
            login_rate_limit_attempts=0,
            secret_encryption_key="test-secret-key",
        ),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app)


def _seed_user(
    session: Session,
    *,
    email: str,
    role: str,
    slug: str,
    password: str = "password",
) -> User:
    identity_repository = IdentityRepository(session)
    account = identity_repository.create_client_account(name=slug.title(), slug=slug)
    return identity_repository.create_user(
        client_account_id=account.id,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )


def _login(client: TestClient, *, email: str, password: str = "password") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    csrf_response = client.get("/auth/csrf")
    assert csrf_response.status_code == 200
    client.headers.update({"X-CSRF-Token": csrf_response.json()["csrf_token"]})


def _admin_client(session: Session) -> TestClient:
    _seed_user(session, email="admin@example.com", role="internal_admin", slug="platform")
    client = _create_client(session)
    _login(client, email="admin@example.com")
    return client


def _sample_post() -> dict[str, object]:
    return {
        "title": "Test Article",
        "excerpt": "Short description",
        "content": "Long content here",
        "author_name": "Tester",
        "is_published": True,
    }


class TestPublicBlogRoutes:
    def test_list_published_posts(self) -> None:
        session = _create_session()
        client = _create_client(session)

        admin = _admin_client(session)
        admin.post("/api/internal/blog/posts", json=_sample_post())

        response = client.get("/api/blog/posts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Article"

    def test_get_post_by_slug(self) -> None:
        session = _create_session()
        client = _create_client(session)

        admin = _admin_client(session)
        admin.post("/api/internal/blog/posts", json={**_sample_post(), "slug": "test-article"})

        response = client.get("/api/blog/posts/test-article")
        assert response.status_code == 200
        assert response.json()["slug"] == "test-article"
        assert "content" in response.json()

    def test_get_post_not_found(self) -> None:
        session = _create_session()
        client = _create_client(session)

        response = client.get("/api/blog/posts/missing")
        assert response.status_code == 404

    def test_list_does_not_include_drafts(self) -> None:
        session = _create_session()
        client = _create_client(session)

        admin = _admin_client(session)
        admin.post("/api/internal/blog/posts", json={**_sample_post(), "is_published": False})

        response = client.get("/api/blog/posts")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_pagination_limit_offset(self) -> None:
        session = _create_session()
        client = _create_client(session)

        admin = _admin_client(session)
        for i in range(5):
            admin.post("/api/internal/blog/posts", json={**_sample_post(), "title": f"Post {i}", "slug": f"post-{i}"})

        response = client.get("/api/blog/posts?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


class TestAdminBlogRoutes:
    def test_create_post(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        response = client.post("/api/internal/blog/posts", json=_sample_post())
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Article"
        assert data["slug"] == "test-article"

    def test_create_post_with_custom_slug(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        response = client.post("/api/internal/blog/posts", json={**_sample_post(), "slug": "custom-slug"})
        assert response.status_code == 201
        assert response.json()["slug"] == "custom-slug"

    def test_create_duplicate_slug_returns_409(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        client.post("/api/internal/blog/posts", json={**_sample_post(), "slug": "dup"})
        response = client.post("/api/internal/blog/posts", json={**_sample_post(), "slug": "dup"})
        assert response.status_code == 409

    def test_list_all_includes_drafts(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        client.post("/api/internal/blog/posts", json={**_sample_post(), "is_published": False, "title": "Draft"})
        client.post("/api/internal/blog/posts", json={**_sample_post(), "is_published": True, "title": "Published"})

        response = client.get("/api/internal/blog/posts")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2

    def test_search_posts(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        client.post("/api/internal/blog/posts", json={**_sample_post(), "title": "Alpha", "slug": "alpha"})
        client.post("/api/internal/blog/posts", json={**_sample_post(), "title": "Beta", "slug": "beta"})

        response = client.get("/api/internal/blog/posts?search=alp")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Alpha"

    def test_update_post(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        create_resp = client.post("/api/internal/blog/posts", json=_sample_post())
        post_id = create_resp.json()["id"]

        response = client.patch(f"/api/internal/blog/posts/{post_id}", json={"title": "Updated"})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    def test_publish_sets_published_at(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        create_resp = client.post("/api/internal/blog/posts", json={**_sample_post(), "is_published": False})
        post_id = create_resp.json()["id"]
        assert create_resp.json()["published_at"] is None

        response = client.patch(f"/api/internal/blog/posts/{post_id}", json={"is_published": True})
        assert response.status_code == 200
        assert response.json()["published_at"] is not None

    def test_delete_post(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        create_resp = client.post("/api/internal/blog/posts", json=_sample_post())
        post_id = create_resp.json()["id"]

        response = client.delete(f"/api/internal/blog/posts/{post_id}")
        assert response.status_code == 204

        get_resp = client.get(f"/api/blog/posts/{create_resp.json()['slug']}")
        assert get_resp.status_code == 404

    def test_delete_missing_returns_404(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        response = client.delete(f"/api/internal/blog/posts/{uuid4()}")
        assert response.status_code == 404

    def test_upload_image(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        from io import BytesIO
        image_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        response = client.post(
            "/api/internal/blog/upload-image",
            files={"image": ("test.png", BytesIO(image_data), "image/png")},
        )
        assert response.status_code == 200
        url = response.json()["url"]
        assert url.startswith("/images/blog/")

    def test_upload_image_too_large(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        from io import BytesIO
        large_data = b"\x00" * (6 * 1024 * 1024)
        response = client.post(
            "/api/internal/blog/upload-image",
            files={"image": ("big.png", BytesIO(large_data), "image/png")},
        )
        assert response.status_code == 422

    def test_upload_image_invalid_mime(self) -> None:
        session = _create_session()
        client = _admin_client(session)

        from io import BytesIO
        response = client.post(
            "/api/internal/blog/upload-image",
            files={"image": ("test.txt", BytesIO(b"not an image"), "text/plain")},
        )
        assert response.status_code == 422
