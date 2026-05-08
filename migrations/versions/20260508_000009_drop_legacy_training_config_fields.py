"""Drop legacy training-config storage columns.

Revision ID: 20260508_000009
Revises: 20260506_000008
Create Date: 2026-05-08 23:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "20260508_000009"
down_revision = "20260506_000008"
branch_labels = None
depends_on = None


def _json_type(bind: sa.engine.Connection) -> sa.types.TypeEngine[object]:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _uuid_type(bind: sa.engine.Connection) -> sa.types.TypeEngine[object]:
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.Uuid(as_uuid=True)


def upgrade() -> None:
    """Remove legacy client_training_configs columns that are no longer used by runtime or API layers."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("client_training_configs")}
    legacy_columns = (
        "default_scenario_id",
        "persona_policy",
        "ui_config",
        "limits",
        "llm_provider_config_id",
    )

    llm_provider_fk = next(
        (
            foreign_key["name"]
            for foreign_key in inspector.get_foreign_keys("client_training_configs")
            if "llm_provider_config_id" in foreign_key.get("constrained_columns", [])
        ),
        None,
    )

    with op.batch_alter_table("client_training_configs") as batch_op:
        if llm_provider_fk and "llm_provider_config_id" in existing_columns:
            batch_op.drop_constraint(llm_provider_fk, type_="foreignkey")
        for column_name in legacy_columns:
            if column_name in existing_columns:
                batch_op.drop_column(column_name)


def downgrade() -> None:
    """Restore legacy client_training_configs columns for older revisions."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("client_training_configs")}
    default_json = sa.text("'{}'::jsonb") if bind.dialect.name == "postgresql" else sa.text("'{}'")
    default_scenario = sa.text("'first_contact_discovery'")
    llm_provider_tables = {table_name for table_name in inspector.get_table_names()}

    with op.batch_alter_table("client_training_configs") as batch_op:
        if "default_scenario_id" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "default_scenario_id",
                    sa.Text(),
                    nullable=False,
                    server_default=default_scenario,
                )
            )
        if "persona_policy" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "persona_policy",
                    _json_type(bind),
                    nullable=False,
                    server_default=default_json,
                )
            )
        if "ui_config" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "ui_config",
                    _json_type(bind),
                    nullable=False,
                    server_default=default_json,
                )
            )
        if "limits" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "limits",
                    _json_type(bind),
                    nullable=False,
                    server_default=default_json,
                )
            )
        if "llm_provider_config_id" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "llm_provider_config_id",
                    _uuid_type(bind),
                    nullable=True,
                )
            )
            if "llm_provider_configs" in llm_provider_tables:
                batch_op.create_foreign_key(
                    "fk_client_training_configs_llm_provider_config_id",
                    "llm_provider_configs",
                    ["llm_provider_config_id"],
                    ["id"],
                )
