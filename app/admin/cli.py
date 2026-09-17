from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.access.repository import AccessRepository
from app.application.persona_generation_service import PersonaGenerationService
from app.application.persona_pool_service import PersonaPoolService
from app.domain.scenarios import list_scenarios
from app.identity.repository import IdentityRepository
from app.identity.roles import UserRole
from app.identity.security import hash_password, PasswordValidationError, validate_permanent_password
from app.history.repository import HistoryRepository
from app.history.service import HistoryService
from app.infrastructure.config import get_settings
from app.infrastructure.db import get_session_factory


class AdminCLIError(Exception):
    pass


def _create_client(
    *,
    identity_repository: IdentityRepository,
    name: str,
    slug: str,
) -> str:
    existing_client = identity_repository.get_client_account_by_slug(slug)
    if existing_client is not None:
        raise AdminCLIError(f"client slug already exists: {slug}")

    client = identity_repository.create_client_account(name=name, slug=slug)
    return f"created client '{client.name}' slug='{client.slug}' id={client.id}"


def _create_user(
    *,
    identity_repository: IdentityRepository,
    client_slug: str,
    email: str,
    password: str,
) -> str:
    client = identity_repository.get_client_account_by_slug(client_slug)
    if client is None:
        raise AdminCLIError(f"client not found: {client_slug}")

    existing_user = identity_repository.get_user_by_email(email)
    if existing_user is not None:
        raise AdminCLIError(f"duplicate email: {email}")

    try:
        validate_permanent_password(password)
    except PasswordValidationError as error:
        raise AdminCLIError(str(error)) from error

    password_hash = hash_password(password)
    user = identity_repository.create_user(
        client_account_id=client.id,
        email=email,
        password_hash=password_hash,
        must_change_password=True,
    )
    return f"created user email='{user.email}' client='{client.slug}' id={user.id}"


def _create_internal_admin(
    *,
    identity_repository: IdentityRepository,
    access_repository: AccessRepository | None = None,
    client_name: str,
    client_slug: str,
    email: str,
    password: str,
) -> str:
    existing_admin = identity_repository.get_first_user_by_role(UserRole.INTERNAL_ADMIN.value)
    if existing_admin is not None:
        raise AdminCLIError("internal admin already exists; use reset-password or DB-admin reviewed flow")

    client = identity_repository.get_client_account_by_slug(client_slug)
    if client is None:
        client = identity_repository.create_client_account(name=client_name, slug=client_slug)

    existing_user = identity_repository.get_user_by_email(email)
    if existing_user is not None:
        raise AdminCLIError(f"duplicate email: {email}")

    try:
        validate_permanent_password(password)
    except PasswordValidationError as error:
        raise AdminCLIError(str(error)) from error

    user = identity_repository.create_user(
        client_account_id=client.id,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.INTERNAL_ADMIN.value,
        must_change_password=True,
    )
    if access_repository is not None:
        access_repository.create_audit_log_record(
            action="internal_admin_bootstrapped",
            entity_type="user",
            entity_id=user.id,
            payload={
                "email": user.email,
                "client_account_id": str(client.id),
                "organization_id": str(client.id),
            },
        )
    return f"created internal admin email='{user.email}' client='{client.slug}' id={user.id}"


def _create_config(
    *,
    identity_repository: IdentityRepository,
    access_repository: AccessRepository,
    client_slug: str,
    name: str,
) -> str:
    client = identity_repository.get_client_account_by_slug(client_slug)
    if client is None:
        raise AdminCLIError(f"client not found: {client_slug}")

    matching_configs = access_repository.list_training_configs_for_client_by_name(
        client_account_id=client.id,
        name=name,
    )
    if matching_configs:
        raise AdminCLIError(f"config already exists for client '{client_slug}': {name}")

    config = access_repository.create_training_config(
        client_account_id=client.id,
        name=name,
    )
    access_repository.create_audit_log_record(
        action="config_created",
        entity_type="client_training_config",
        entity_id=config.id,
        payload={"client_slug": client.slug, "name": config.name},
    )
    return f"created config '{config.name}' client='{client.slug}' id={config.id}"


def _assign_config(
    *,
    identity_repository: IdentityRepository,
    access_repository: AccessRepository,
    email: str,
    config_name: str,
    is_default: bool,
) -> str:
    user = identity_repository.get_user_by_email(email)
    if user is None:
        raise AdminCLIError(f"user not found: {email}")

    matching_configs = access_repository.list_training_configs_for_client_by_name(
        client_account_id=user.client_account_id,
        name=config_name,
    )
    if not matching_configs:
        raise AdminCLIError(f"config not found: {config_name}")
    if len(matching_configs) > 1:
        raise AdminCLIError(f"multiple configs found with name '{config_name}' for user's client")

    assignment = access_repository.assign_training_config_to_user(
        user_id=user.id,
        training_config_id=matching_configs[0].id,
        is_default=is_default,
    )
    access_repository.create_audit_log_record(
        action="config_assigned",
        entity_type="client_training_config",
        actor_user_id=user.id,
        entity_id=matching_configs[0].id,
        payload={"email": user.email, "default": assignment.is_default},
    )
    return (
        f"assigned config '{matching_configs[0].name}' to '{user.email}'"
        f" default={str(assignment.is_default).lower()}"
    )


def _update_config(
    *,
    identity_repository: IdentityRepository,
    access_repository: AccessRepository,
    client_slug: str,
    config_name: str,
    new_name: str | None = None,
) -> str:
    client = identity_repository.get_client_account_by_slug(client_slug)
    if client is None:
        raise AdminCLIError(f"client not found: {client_slug}")

    matching_configs = access_repository.list_training_configs_for_client_by_name(
        client_account_id=client.id,
        name=config_name,
    )
    if not matching_configs:
        raise AdminCLIError(f"config not found: {config_name}")
    if len(matching_configs) > 1:
        raise AdminCLIError(f"multiple configs found with name '{config_name}' for client '{client_slug}'")

    config = access_repository.update_training_config(
        training_config_id=matching_configs[0].id,
        name=new_name,
    )
    if config is None:
        raise AdminCLIError(f"config not found: {config_name}")

    access_repository.create_audit_log_record(
        action="config_updated",
        entity_type="client_training_config",
        entity_id=config.id,
        payload={"client_slug": client.slug, "name": config.name},
    )
    return f"updated config '{config.name}' client='{client.slug}' id={config.id}"


def _reset_password(
    *,
    identity_repository: IdentityRepository,
    access_repository: AccessRepository | None = None,
    email: str,
    password: str,
) -> str:
    user = identity_repository.get_user_by_email(email)
    if user is None:
        raise AdminCLIError(f"user not found: {email}")

    try:
        validate_permanent_password(password)
    except PasswordValidationError as error:
        raise AdminCLIError(str(error)) from error

    password_hash = hash_password(password)
    updated_user = identity_repository.update_user_password(
        user_id=user.id,
        password_hash=password_hash,
        must_change_password=True,
    )
    if updated_user is None:
        raise AdminCLIError(f"user not found: {email}")
    if access_repository is not None:
        access_repository.create_audit_log_record(
            action="password_reset",
            entity_type="user",
            entity_id=updated_user.id,
            payload={"email": updated_user.email},
        )
    return f"password reset for '{updated_user.email}'"


def _disable_user(
    *,
    identity_repository: IdentityRepository,
    access_repository: AccessRepository | None = None,
    email: str,
) -> str:
    user = identity_repository.get_user_by_email(email)
    if user is None:
        raise AdminCLIError(f"user not found: {email}")

    updated_user = identity_repository.disable_user(user_id=user.id)
    if updated_user is None:
        raise AdminCLIError(f"user not found: {email}")
    if access_repository is not None:
        access_repository.create_audit_log_record(
            action="user_disabled",
            entity_type="user",
            entity_id=updated_user.id,
            payload={"email": updated_user.email},
        )
    return f"user disabled: '{updated_user.email}'"


def _cleanup_expired_sessions(*, identity_repository: IdentityRepository) -> str:
    deleted_count = identity_repository.delete_expired_login_sessions(expired_before=datetime.now(UTC))
    return f"cleaned up expired login sessions: {deleted_count}"


def _snapshot_token_usage(
    *,
    history_service: HistoryService,
    date_str: str | None = None,
) -> str:
    from datetime import UTC, datetime, timedelta
    from zoneinfo import ZoneInfo

    msk = ZoneInfo("Europe/Moscow")
    if date_str:
        snapshot_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=msk)
    else:
        snapshot_date = datetime.now(tz=msk).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)

    # Snapshot all organizations. In a real deployment this would iterate over all client accounts.
    # For MVP, we snapshot all organizations that have token usage records.
    from app.identity.models import ClientAccount
    from sqlalchemy import select

    session = history_service._repository._session
    orgs = session.scalars(select(ClientAccount.id)).all()
    created = 0
    for org_id in orgs:
        try:
            history_service.create_token_usage_snapshot(
                client_account_id=org_id,
                snapshot_date=snapshot_date,
            )
            created += 1
        except Exception:
            session.rollback()
            raise
    return f"created {created} snapshots for date {snapshot_date.date()}"


def _warm_persona_pool(*, db_session, scenario_ids: list[str] | None) -> str:  # type: ignore[no-untyped-def]
    """Refill the pre-generated persona reserve for active training configs."""
    settings = get_settings()
    resolved_scenario_ids = scenario_ids or [scenario.id for scenario in list_scenarios()]
    generation_service = PersonaGenerationService(db_session, settings=settings)
    pool_service = PersonaPoolService(
        db_session,
        generation_service=generation_service,
        low_watermark=settings.persona_pool_low_watermark,
        target_size=settings.persona_pool_target_size if settings.persona_pool_enabled else 0,
        refill_batch_size=settings.persona_pool_refill_batch_size,
    )
    if not pool_service.enabled:
        return "persona pool is disabled (PERSONA_POOL_TARGET_SIZE=0 or PERSONA_POOL_ENABLED=false)"
    results = pool_service.refill_all_active_configs(scenario_ids=resolved_scenario_ids)
    return f"generated {len(results)} personas for {len(resolved_scenario_ids)} scenario(s)"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.admin.cli",
        description="Internal admin CLI for clients, users, and training configs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_client_parser = subparsers.add_parser("create-client")
    create_client_parser.add_argument("--name", required=True)
    create_client_parser.add_argument("--slug", required=True)

    create_user_parser = subparsers.add_parser("create-user")
    create_user_parser.add_argument("--client", required=True)
    create_user_parser.add_argument("--email", required=True)
    create_user_parser.add_argument("--password", required=True)

    create_internal_admin_parser = subparsers.add_parser("create-internal-admin")
    create_internal_admin_parser.add_argument("--client-name", required=True)
    create_internal_admin_parser.add_argument("--client-slug", required=True)
    create_internal_admin_parser.add_argument("--email", required=True)
    create_internal_admin_parser.add_argument("--password", required=True)

    create_config_parser = subparsers.add_parser("create-config")
    create_config_parser.add_argument("--client", required=True)
    create_config_parser.add_argument("--name", required=True)

    assign_config_parser = subparsers.add_parser("assign-config")
    assign_config_parser.add_argument("--email", required=True)
    assign_config_parser.add_argument("--config", required=True)
    assign_config_parser.add_argument("--default", action="store_true")

    update_config_parser = subparsers.add_parser("update-config")
    update_config_parser.add_argument("--client", required=True)
    update_config_parser.add_argument("--config", required=True)
    update_config_parser.add_argument("--name")

    reset_password_parser = subparsers.add_parser("reset-password")
    reset_password_parser.add_argument("--email", required=True)
    reset_password_parser.add_argument("--password", required=True)

    disable_user_parser = subparsers.add_parser("disable-user")
    disable_user_parser.add_argument("--email", required=True)

    subparsers.add_parser("cleanup-expired-sessions")

    snapshot_parser = subparsers.add_parser("snapshot-token-usage")
    snapshot_parser.add_argument("--date", help="YYYY-MM-DD (default: yesterday)")

    warm_pool_parser = subparsers.add_parser("warm-persona-pool")
    warm_pool_parser.add_argument(
        "--scenario-id",
        action="append",
        dest="scenario_ids",
        help="Scenario id to refill (repeatable; default: all universal scenarios)",
    )

    return parser


def run_cli(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Keep Settings as the single source for DB/environment configuration.
    get_settings()
    session_factory = get_session_factory()

    with session_factory() as session:
        identity_repository = IdentityRepository(session)
        access_repository = AccessRepository(session)
        try:
            if args.command == "create-client":
                message = _create_client(
                    identity_repository=identity_repository,
                    name=args.name,
                    slug=args.slug,
                )
            elif args.command == "create-user":
                message = _create_user(
                    identity_repository=identity_repository,
                    client_slug=args.client,
                    email=args.email,
                    password=args.password,
                )
            elif args.command == "create-internal-admin":
                message = _create_internal_admin(
                    identity_repository=identity_repository,
                    access_repository=access_repository,
                    client_name=args.client_name,
                    client_slug=args.client_slug,
                    email=args.email,
                    password=args.password,
                )
            elif args.command == "create-config":
                message = _create_config(
                    identity_repository=identity_repository,
                    access_repository=access_repository,
                    client_slug=args.client,
                    name=args.name,
                )
            elif args.command == "assign-config":
                message = _assign_config(
                    identity_repository=identity_repository,
                    access_repository=access_repository,
                    email=args.email,
                    config_name=args.config,
                    is_default=args.default,
                )
            elif args.command == "update-config":
                message = _update_config(
                    identity_repository=identity_repository,
                    access_repository=access_repository,
                    client_slug=args.client,
                    config_name=args.config,
                    new_name=args.name,
                )
            elif args.command == "reset-password":
                message = _reset_password(
                    identity_repository=identity_repository,
                    access_repository=access_repository,
                    email=args.email,
                    password=args.password,
                )
            elif args.command == "disable-user":
                message = _disable_user(
                    identity_repository=identity_repository,
                    access_repository=access_repository,
                    email=args.email,
                )
            elif args.command == "snapshot-token-usage":
                history_repository = HistoryRepository(session)
                history_service = HistoryService(history_repository)
                message = _snapshot_token_usage(
                    history_service=history_service,
                    date_str=args.date,
                )
            elif args.command == "warm-persona-pool":
                message = _warm_persona_pool(
                    db_session=session,
                    scenario_ids=args.scenario_ids,
                )
            else:
                message = _cleanup_expired_sessions(identity_repository=identity_repository)
        except IntegrityError as error:
            session.rollback()
            print(f"Error: database constraint violation: {error.__class__.__name__}", file=sys.stderr)
            return 1
        except AdminCLIError as error:
            session.rollback()
            print(f"Error: {error}", file=sys.stderr)
            return 1

    print(message)
    return 0


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
