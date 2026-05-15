import { FormEvent } from "react";
import { Badge, EmptyState } from "../components/AdminPrimitives";
import type { TrainingConfigDTO } from "../types";
import { statusLabel } from "../utils";

export type ConfigForm = {
  id?: string;
  name: string;
  persona_generation_context: string;
};

export const DEFAULT_CONFIG_FORM: ConfigForm = {
  name: "",
  persona_generation_context: "",
};

export function OrganizationTrainingConfigsTab(props: {
  configs: TrainingConfigDTO[];
  form: ConfigForm;
  setForm: (form: ConfigForm) => void;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (config: TrainingConfigDTO) => void;
}) {
  /** Render simplified training config form and config list. */
  return (
    <section className="admin-panel">
      <div className="admin-panel__header">
        <h2>Настройки тренировок</h2>
      </div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <div className="admin-form-grid">
          <label>
            <span>Название</span>
            <input
              value={props.form.name}
              onChange={(event) => props.setForm({ ...props.form, name: event.target.value })}
              required
            />
          </label>
        </div>
        <label>
          <span>Контекст генерации личности</span>
          <textarea
            rows={8}
            value={props.form.persona_generation_context}
            onChange={(event) => props.setForm({ ...props.form, persona_generation_context: event.target.value })}
          />
          <small className="admin-muted">
            Опишите продукт клиента, целевую аудиторию, типичные роли ЛПР, боли, возражения, критерии выбора и ограничения.
          </small>
        </label>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>
          {props.form.id ? "Обновить настройку" : "Создать настройку"}
        </button>
      </form>
      {props.configs.length === 0 ? (
        <EmptyState title="Настроек тренировок нет" />
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Контекст</th>
                <th>Статус</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {props.configs.map((config) => (
                <tr key={config.id}>
                  <td>{config.name}</td>
                  <td>
                    {config.persona_generation_context
                      ? `${config.persona_generation_context.slice(0, 120)}${
                          config.persona_generation_context.length > 120 ? "..." : ""
                        }`
                      : "—"}
                  </td>
                  <td>
                    <Badge tone={config.is_active ? "good" : "danger"}>{statusLabel(config.is_active)}</Badge>
                  </td>
                  <td>
                    <div className="admin-row-actions">
                      <button
                        type="button"
                        className="admin-link-button"
                        onClick={() =>
                          props.setForm({
                            id: config.id,
                            name: config.name,
                            persona_generation_context: config.persona_generation_context,
                          })
                        }
                      >
                        Изменить
                      </button>
                      <button
                        type="button"
                        className="admin-link-button"
                        onClick={() => props.onToggle(config)}
                      >
                        {config.is_active ? "Отключить" : "Включить"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
