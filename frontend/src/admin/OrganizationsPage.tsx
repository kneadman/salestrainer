import { FormEvent, useEffect, useMemo, useState } from "react";
import { createOrganization, disableOrganization, enableOrganization, listOrganizations, updateOrganization } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState } from "./components/AdminPrimitives";
import type { OrganizationDTO } from "./types";
import { buildOrganizationViewModel } from "../viewModels";
import { getErrorMessage } from "../errorMessage";

type OrganizationsPageProps = {
  onNavigate: (path: string) => void;
};

type OrganizationForm = {
  id?: string;
  name: string;
  slug: string;
};

export function OrganizationsPage({ onNavigate }: OrganizationsPageProps) {
  /** Render organization list, client-side search, and create/edit actions. */
  const [organizations, setOrganizations] = useState<OrganizationDTO[]>([]);
  const [filter, setFilter] = useState("");
  const [form, setForm] = useState<OrganizationForm>({ name: "", slug: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = async () => {
    /** Refresh organization rows from the internal API. */
    setLoading(true);
    setError(null);
    try {
      setOrganizations(await listOrganizations());
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    /** Load organizations on initial page mount. */
    void load();
  }, []);

  const visibleOrganizations = useMemo(() => {
    /** Apply local name/slug search without changing backend API contracts. */
    const needle = filter.trim().toLowerCase();
    if (!needle) {
      return organizations;
    }
    return organizations.filter((org) => `${org.name} ${org.slug}`.toLowerCase().includes(needle));
  }, [filter, organizations]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    /** Create or update an organization and show backend validation errors. */
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      if (form.id) {
        await updateOrganization(form.id, { name: form.name, slug: form.slug });
        setSuccess("Организация обновлена.");
      } else {
        await createOrganization({ name: form.name, slug: form.slug });
        setSuccess("Организация создана.");
      }
      setForm({ name: "", slug: "" });
      await load();
    } catch (saveError) {
      setError(getErrorMessage(saveError));
    } finally {
      setSaving(false);
    }
  };

  const toggleOrganization = async (org: OrganizationDTO) => {
    /** Enable or disable one organization after a destructive-action confirmation. */
    if (org.is_active && !window.confirm(`Отключить организацию ${org.name}?`)) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      if (org.is_active) {
        await disableOrganization(org.id);
        setSuccess("Организация отключена.");
      } else {
        await enableOrganization(org.id);
        setSuccess("Организация включена.");
      }
      await load();
    } catch (toggleError) {
      setError(getErrorMessage(toggleError));
    }
  };

  if (loading) {
    return <LoadingState title="Загрузка организаций" />;
  }

  if (error && organizations.length === 0) {
    return <ErrorState title="Организации недоступны" detail={error} />;
  }

  const orgVms = visibleOrganizations.map(buildOrganizationViewModel);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <span className="admin-kicker">Клиентские аккаунты</span>
          <h1>Организации</h1>
        </div>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      {success ? <div className="admin-alert">{success}</div> : null}
      <section className="admin-panel">
        <form className="admin-form admin-form--inline" onSubmit={handleSubmit}>
          <label>
            <span>Название</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </label>
          <label>
            <span>Slug</span>
            <input
              value={form.slug}
              pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
              title="Используйте латиницу в нижнем регистре, цифры и дефисы."
              onChange={(event) => setForm({ ...form, slug: event.target.value })}
              required
            />
          </label>
          <button type="submit" className="admin-button admin-button--primary" disabled={saving}>
            {form.id ? "Обновить" : "Создать"}
          </button>
          {form.id ? (
            <button type="button" className="admin-button" onClick={() => setForm({ name: "", slug: "" })}>
              Отмена
            </button>
          ) : null}
        </form>
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header">
          <h2>Список организаций</h2>
          <input className="admin-search" placeholder="Поиск по названию или slug" value={filter} onChange={(event) => setFilter(event.target.value)} />
        </div>
        {visibleOrganizations.length === 0 ? (
          <EmptyState title="Организаций нет" detail="Создайте первую организацию, чтобы настроить доступ клиента." />
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Slug</th>
                  <th>Статус</th>
                  <th>Пользователи</th>
                  <th>Конфиги</th>
                  <th>Обновлено</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {orgVms.map((vm, index) => {
                  const org = visibleOrganizations[index];
                  return (
                    <tr key={vm.id}>
                      <td>{vm.name}</td>
                      <td>{vm.slug}</td>
                      <td><Badge tone={vm.statusTone}>{vm.statusLabel}</Badge></td>
                      <td>{org.active_users_count}/{org.users_count}</td>
                      <td>{org.training_configs_count}</td>
                      <td>{vm.updatedAtLabel}</td>
                      <td>
                        <div className="admin-row-actions">
                          <a href={`/admin/organizations/${org.id}`} className="admin-link-button" onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate(`/admin/organizations/${org.id}`); }}>
                            Открыть
                          </a>
                          <button type="button" className="admin-link-button" onClick={() => setForm({ id: org.id, name: org.name, slug: org.slug })}>
                            Изменить
                          </button>
                          <button type="button" className="admin-link-button" onClick={() => void toggleOrganization(org)}>
                            {org.is_active ? "Отключить" : "Включить"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
