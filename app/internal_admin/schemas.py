from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.identity.roles import UserRole
from app.domain.scenarios import SCENARIOS

NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
PasswordStr = Annotated[str, StringConstraints(min_length=8, max_length=256)]
SlugStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
ScenarioIdStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ClientUserRole(StrEnum):
    CLIENT_LEAD = "client_lead"
    CLIENT_MANAGER = "client_manager"


class LLMProvider(StrEnum):
    YANDEX_COMPATIBLE = "yandex_compatible"
    OPENAI_COMPATIBLE = "openai_compatible"
    FAKE = "fake"


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

    name: NameStr
    slug: SlugStr


class OrganizationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NameStr | None = None
    slug: SlugStr | None = None


class ClientAccountBriefDTO(BaseModel):
    id: UUID
    name: str
    slug: str


class UserDTO(BaseModel):
    id: UUID
    client_account_id: UUID
    email: EmailStr
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    client_account: ClientAccountBriefDTO | None = None


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: PasswordStr
    role: ClientUserRole


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    role: ClientUserRole | None = None


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: PasswordStr


class TrainingConfigDTO(BaseModel):
    id: UUID
    client_account_id: UUID
    name: str
    is_active: bool
    default_scenario_id: str
    persona_generation_prompt: str
    persona_policy: dict[str, object]
    ui_config: dict[str, object]
    limits: dict[str, object]
    llm_provider_config_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TrainingConfigCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NameStr
    default_scenario_id: ScenarioIdStr
    persona_generation_prompt: str = ""
    persona_policy: dict[str, object] = Field(default_factory=dict)
    ui_config: dict[str, object] = Field(default_factory=dict)
    limits: dict[str, object] = Field(default_factory=dict)
    llm_provider_config_id: UUID | None = None

    @field_validator("default_scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str) -> str:
        if value not in SCENARIOS:
            raise ValueError("Unknown scenario_id.")
        return value


class TrainingConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NameStr | None = None
    default_scenario_id: ScenarioIdStr | None = None
    persona_generation_prompt: str | None = None
    persona_policy: dict[str, object] | None = None
    ui_config: dict[str, object] | None = None
    limits: dict[str, object] | None = None
    llm_provider_config_id: UUID | None = None

    @field_validator("default_scenario_id")
    @classmethod
    def validate_scenario_id(cls, value: str | None) -> str | None:
        if value is not None and value not in SCENARIOS:
            raise ValueError("Unknown scenario_id.")
        return value


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
    has_api_key: bool = False
    api_key_preview: str | None = None
    has_persona_api_key: bool
    persona_api_key_preview: str | None
    persona_folder_id: str | None
    persona_agent_id: str | None
    persona_master_prompt: str | None
    persona_json_template: str | None
    has_dialogue_api_key: bool
    dialogue_api_key_preview: str | None
    dialogue_folder_id: str | None
    dialogue_agent_id: str | None
    dialogue_master_prompt: str | None
    dialogue_json_template: str | None
    created_at: datetime
    updated_at: datetime


class LLMProviderConfigCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NameStr
    provider: LLMProvider = LLMProvider.YANDEX_COMPATIBLE
    persona_api_key: Annotated[str, StringConstraints(max_length=4096)] | None = None
    persona_folder_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    persona_agent_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    persona_master_prompt: Annotated[str, StringConstraints(max_length=20000)] | None = None
    persona_json_template: Annotated[str, StringConstraints(max_length=20000)] | None = None
    dialogue_api_key: Annotated[str, StringConstraints(max_length=4096)] | None = None
    dialogue_folder_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    dialogue_agent_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    dialogue_master_prompt: Annotated[str, StringConstraints(max_length=20000)] | None = None
    dialogue_json_template: Annotated[str, StringConstraints(max_length=20000)] | None = None
    api_key: Annotated[str, StringConstraints(max_length=4096)] | None = None
    folder_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    agent_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    base_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=512)] | None = None
    model_or_agent_label: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None

    @field_validator(
        "persona_api_key",
        "persona_folder_id",
        "persona_agent_id",
        "persona_master_prompt",
        "persona_json_template",
        "dialogue_api_key",
        "dialogue_folder_id",
        "dialogue_agent_id",
        "dialogue_master_prompt",
        "dialogue_json_template",
        "api_key",
        "folder_id",
        "agent_id",
        "base_url",
        "model_or_agent_label",
        mode="before",
    )
    @classmethod
    def blank_strings_to_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class LLMProviderConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NameStr | None = None
    provider: LLMProvider | None = None
    persona_api_key: Annotated[str, StringConstraints(max_length=4096)] | None = None
    persona_folder_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    persona_agent_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    persona_master_prompt: Annotated[str, StringConstraints(max_length=20000)] | None = None
    persona_json_template: Annotated[str, StringConstraints(max_length=20000)] | None = None
    dialogue_api_key: Annotated[str, StringConstraints(max_length=4096)] | None = None
    dialogue_folder_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    dialogue_agent_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    dialogue_master_prompt: Annotated[str, StringConstraints(max_length=20000)] | None = None
    dialogue_json_template: Annotated[str, StringConstraints(max_length=20000)] | None = None
    api_key: Annotated[str, StringConstraints(max_length=4096)] | None = None
    folder_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    agent_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None
    base_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=512)] | None = None
    model_or_agent_label: Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)] | None = None

    _blank_strings_to_none = field_validator(
        "persona_api_key",
        "persona_folder_id",
        "persona_agent_id",
        "persona_master_prompt",
        "persona_json_template",
        "dialogue_api_key",
        "dialogue_folder_id",
        "dialogue_agent_id",
        "dialogue_master_prompt",
        "dialogue_json_template",
        "api_key",
        "folder_id",
        "agent_id",
        "base_url",
        "model_or_agent_label",
        mode="before",
    )(LLMProviderConfigCreateRequest.blank_strings_to_none)


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
