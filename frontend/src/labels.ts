export function roleLabel(role: string): string {
  const labels: Record<string, string> = {
    internal_admin: "Администратор платформы",
    client_lead: "Руководитель",
    client_manager: "Менеджер",
    client_user: "Менеджер",
  };
  return labels[role] ?? "Пользователь";
}

export function statusLabel(value: string | boolean | null | undefined): string {
  if (typeof value === "boolean") {
    return value ? "Включено" : "Отключено";
  }
  const labels: Record<string, string> = {
    active: "Активна",
    finished: "Завершена",
    expired: "Истекла",
    disabled: "Отключено",
    enabled: "Включено",
  };
  return value ? labels[value] ?? "Неизвестный статус" : "Не указано";
}

export function scenarioLabel(id: string | null | undefined): string {
  const labels: Record<string, string> = {
    first_contact_discovery: "Первичный контакт и разведка",
    qualification_and_authority: "Квалификация и полномочия",
    needs_diagnosis: "Диагностика потребностей",
    objection_handling: "Работа с возражениями",
    price_and_value: "Цена и ценность",
    bad_experience_recovery: "Восстановление доверия",
    next_step_booking: "Назначение следующего шага",
    follow_up_after_pause: "Возврат после паузы",
    generic_b2b_first_contact: "Первичный контакт и разведка",
    sales_audit_cold_outreach: "Первичный контакт и разведка",
    accounting_outsource_cold_outreach: "Первичный контакт и разведка",
  };
  return id ? labels[id] ?? "Другой сценарий" : "Не указано";
}

export function stageLabel(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    first_contact: "Первичный контакт",
    initial_contact: "Первичный контакт",
    role_discovery: "Выявление роли",
    role_qualification: "Выявление роли",
    need_discovery: "Выявление потребностей",
    discovery: "Выявление потребностей",
    qualification: "Выявление потребностей",
    value_clarification: "Уточнение ценности",
    value_discussion: "Уточнение ценности",
    objection_handling: "Работа с возражениями",
    trust_building: "Укрепление доверия",
    next_step_negotiation: "Согласование следующего шага",
    next_step: "Согласование следующего шага",
    finished_success: "Успешно завершена",
    closed_won: "Успешно завершена",
    finished_failed: "Завершена без результата",
    closed_lost: "Завершена без результата",
  };
  return value ? labels[value] ?? "Другой этап" : "Не указан";
}

export function auditActionLabel(action: string | null | undefined): string {
  const labels: Record<string, string> = {
    organization_created: "Организация создана",
    organization_updated: "Организация обновлена",
    organization_disabled: "Организация отключена",
    organization_enabled: "Организация включена",
    user_created: "Пользователь создан",
    user_updated: "Пользователь обновлён",
    user_disabled: "Пользователь отключён",
    user_enabled: "Пользователь включён",
    password_reset: "Пароль сброшен",
    password_changed: "Пароль изменён",
    internal_admin_bootstrapped: "Администратор платформы создан",
    config_created: "Настройка тренировки создана",
    config_updated: "Настройка тренировки обновлена",
    config_assigned: "Настройка назначена",
    training_config_created: "Настройка тренировки создана",
    training_config_updated: "Настройка тренировки обновлена",
    training_config_disabled: "Настройка тренировки отключена",
    training_config_enabled: "Настройка тренировки включена",
    training_config_assigned: "Настройка назначена",
    training_config_unassigned: "Настройка снята",
    default_training_config_changed: "Настройка по умолчанию изменена",
    llm_provider_config_created: "Провайдер модели создан",
    llm_provider_config_updated: "Провайдер модели обновлён",
    llm_provider_config_enabled: "Провайдер модели включён",
    llm_provider_config_disabled: "Провайдер модели отключён",
    login_success: "Вход выполнен",
    login_failed: "Ошибка входа",
    logout: "Выход",
  };
  return action ? labels[action] ?? "Системное событие" : "Системное событие";
}

export function auditEntityLabel(entityType: string | null | undefined): string {
  const labels: Record<string, string> = {
    organization: "Организация",
    user: "Пользователь",
    training_config: "Настройка тренировки",
    client_training_config: "Настройка тренировки",
    user_training_config: "Назначение настройки",
    llm_provider_config: "Провайдер модели",
    login_session: "Сессия входа",
  };
  return entityType ? labels[entityType] ?? "Системный объект" : "Системный объект";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}
