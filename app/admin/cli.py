from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.access.repository import AccessRepository
from app.identity.repository import IdentityRepository
from app.identity.roles import UserRole
from app.identity.security import hash_password
from app.infrastructure.config import get_settings
from app.infrastructure.db import get_session_factory


class AdminCLIError(Exception):
    pass


def _load_persona_policy(path: str) -> dict[str, object]:
    file_path = Path(path)
    if not file_path.exists():
        raise AdminCLIError(f"persona policy file not found: {file_path}")

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AdminCLIError(f"invalid JSON in persona policy file: {file_path}") from error

    if not isinstance(payload, dict):
        raise AdminCLIError("persona policy must be a JSON object")

    return payload


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
    scenario_id: str,
    persona_policy_file: str,
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

    persona_policy = _load_persona_policy(persona_policy_file)
    config = access_repository.create_training_config(
        client_account_id=client.id,
        name=name,
        default_scenario_id=scenario_id,
        persona_policy=persona_policy,
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
    scenario_id: str | None = None,
    persona_policy_file: str | None = None,
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

    persona_policy = _load_persona_policy(persona_policy_file) if persona_policy_file else None
    config = access_repository.update_training_config(
        training_config_id=matching_configs[0].id,
        name=new_name,
        default_scenario_id=scenario_id,
        persona_policy=persona_policy,
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
    create_config_parser.add_argument("--scenario", required=True)
    create_config_parser.add_argument("--persona-policy-file", required=True)

    assign_config_parser = subparsers.add_parser("assign-config")
    assign_config_parser.add_argument("--email", required=True)
    assign_config_parser.add_argument("--config", required=True)
    assign_config_parser.add_argument("--default", action="store_true")

    update_config_parser = subparsers.add_parser("update-config")
    update_config_parser.add_argument("--client", required=True)
    update_config_parser.add_argument("--config", required=True)
    update_config_parser.add_argument("--name")
    update_config_parser.add_argument("--scenario")
    update_config_parser.add_argument("--persona-policy-file")

    reset_password_parser = subparsers.add_parser("reset-password")
    reset_password_parser.add_argument("--email", required=True)
    reset_password_parser.add_argument("--password", required=True)

    disable_user_parser = subparsers.add_parser("disable-user")
    disable_user_parser.add_argument("--email", required=True)

    subparsers.add_parser("cleanup-expired-sessions")

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
                    scenario_id=args.scenario,
                    persona_policy_file=args.persona_policy_file,
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
                    scenario_id=args.scenario,
                    persona_policy_file=args.persona_policy_file,
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
