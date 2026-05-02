from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.identity.roles import UserRole


class OrganizationDTO(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    users_count: int
    active_users_count: int
    training_configs_count: int


class OrganizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str


class OrganizationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    slug: str | None = None


class ClientAccountBriefDTO(BaseModel):
    id: UUID
    name: str
    slug: str


class UserDTO(BaseModel):
    id: UUID
    client_account_id: UUID
    email: str
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    client_account: ClientAccountBriefDTO | None = None


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    role: UserRole


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    role: UserRole | None = None


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str


class TrainingConfigDTO(BaseModel):
    id: UUID
    client_account_id: UUID
    name: str
    is_active: bool
    default_scenario_id: str
    product_line: str
    persona_policy: dict[str, object]
    ui_config: dict[str, object]
    limits: dict[str, object]
    llm_provider_config_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TrainingConfigCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    default_scenario_id: str
    product_line: str
    persona_policy: dict[str, object] = Field(default_factory=dict)
    ui_config: dict[str, object] = Field(default_factory=dict)
    limits: dict[str, object] = Field(default_factory=dict)
    llm_provider_config_id: UUID | None = None


class TrainingConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    default_scenario_id: str | None = None
    product_line: str | None = None
    persona_policy: dict[str, object] | None = None
    ui_config: dict[str, object] | None = None
    limits: dict[str, object] | None = None
    llm_provider_config_id: UUID | None = None


class UserTrainingConfigAssignmentDTO(BaseModel):
    user_id: UUID
    training_config_id: UUID
    is_default: bool
    training_config: TrainingConfigDTO


class LLMProviderConfigDTO(BaseModel):
    id: UUID
    client_account_id: UUID
    name: str
    provider: str
    is_active: bool
    has_api_key: bool
    api_key_preview: str | None
    folder_id: str | None
    agent_id: str | None
    base_url: str | None
    model_or_agent_label: str | None
    created_at: datetime
    updated_at: datetime


class LLMProviderConfigCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    provider: str = "yandex_compatible"
    api_key: str | None = None
    folder_id: str | None = None
    agent_id: str | None = None
    base_url: str | None = None
    model_or_agent_label: str | None = None


class LLMProviderConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    provider: str | None = None
    api_key: str | None = None
    folder_id: str | None = None
    agent_id: str | None = None
    base_url: str | None = None
    model_or_agent_label: str | None = None


class AuditLogDTO(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    payload: dict[str, object]
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
