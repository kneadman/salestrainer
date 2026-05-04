export function roleLabel(role: string): string {
  const labels: Record<string, string> = {
    internal_admin: "Администратор платформы",
    client_lead: "Руководитель",
    client_manager: "Менеджер",
    client_user: "Менеджер",
  };
  return labels[role] ?? role;
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
  return value ? labels[value] ?? value : "Не указано";
}

export function scenarioLabel(id: string | null | undefined): string {
  const labels: Record<string, string> = {
    generic_b2b_first_contact: "Первичный B2B-контакт",
    sales_audit_cold_outreach: "Аудит отдела продаж",
    accounting_outsource_cold_outreach: "Бухгалтерский аутсорсинг",
  };
  return id ? labels[id] ?? id : "Не указано";
}

export function productLineLabel(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    accounting_outsourcing: "Бухгалтерский аутсорсинг",
    outsourced_cfo: "Финансовый директор на аутсорсинге",
  };
  return value ? labels[value] ?? value : "Не указано";
}

export function providerLabel(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    yandex_compatible: "Yandex AI Studio",
    openai_compatible: "OpenAI-compatible",
    fake: "Локальная тестовая модель",
  };
  return value ? labels[value] ?? value : "Не указано";
}

export function metricNameLabel(key: string): string {
  const labels: Record<string, string> = {
    final_interest_score: "Итоговый интерес",
    turn_count: "Количество сообщений",
    client_account_id: "ID организации",
    session_id: "ID сессии",
    training_config_id: "ID конфига",
    scenario_id: "Сценарий",
    status: "Статус",
  };
  return labels[key] ?? key.replace(/_/g, " ");
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
