import { FormEvent, useEffect, useMemo, useState } from "react";
import { createOrganization, disableOrganization, enableOrganization, listOrganizations, updateOrganization } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState } from "./components/AdminPrimitives";
import type { OrganizationDTO } from "./types";
import { formatDate, getErrorMessage, statusLabel } from "./utils";

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
        setSuccess("Organization updated.");
      } else {
        await createOrganization({ name: form.name, slug: form.slug });
        setSuccess("Organization created.");
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
    if (org.is_active && !window.confirm(`Disable organization ${org.name}?`)) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      if (org.is_active) {
        await disableOrganization(org.id);
        setSuccess("Organization disabled.");
      } else {
        await enableOrganization(org.id);
        setSuccess("Organization enabled.");
      }
      await load();
    } catch (toggleError) {
      setError(getErrorMessage(toggleError));
    }
  };

  if (loading) {
    return <LoadingState title="Loading organizations" />;
  }

  if (error && organizations.length === 0) {
    return <ErrorState title="Organizations unavailable" detail={error} />;
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <span className="admin-kicker">Platform tenants</span>
          <h1>Organizations</h1>
        </div>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      {success ? <div className="admin-alert">{success}</div> : null}
      <section className="admin-panel">
        <form className="admin-form admin-form--inline" onSubmit={handleSubmit}>
          <label>
            <span>Name</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </label>
          <label>
            <span>Slug</span>
            <input
              value={form.slug}
              pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
              title="Use lowercase latin letters, numbers, and hyphens."
              onChange={(event) => setForm({ ...form, slug: event.target.value })}
              required
            />
          </label>
          <button type="submit" className="admin-button admin-button--primary" disabled={saving}>
            {form.id ? "Update" : "Create"}
          </button>
          {form.id ? (
            <button type="button" className="admin-button" onClick={() => setForm({ name: "", slug: "" })}>
              Cancel
            </button>
          ) : null}
        </form>
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header">
          <h2>Organization list</h2>
          <input className="admin-search" placeholder="Search name or slug" value={filter} onChange={(event) => setFilter(event.target.value)} />
        </div>
        {visibleOrganizations.length === 0 ? (
          <EmptyState title="No organizations" detail="Create the first organization to start configuring client access." />
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Slug</th>
                  <th>Status</th>
                  <th>Users</th>
                  <th>Configs</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleOrganizations.map((org) => (
                  <tr key={org.id}>
                    <td>{org.name}</td>
                    <td>{org.slug}</td>
                    <td><Badge tone={org.is_active ? "good" : "danger"}>{statusLabel(org.is_active)}</Badge></td>
                    <td>{org.active_users_count}/{org.users_count}</td>
                    <td>{org.training_configs_count}</td>
                    <td>{formatDate(org.updated_at)}</td>
                    <td>
                      <div className="admin-row-actions">
                        <button type="button" className="admin-link-button" onClick={() => onNavigate(`/admin/organizations/${org.id}`)}>
                          Open
                        </button>
                        <button type="button" className="admin-link-button" onClick={() => setForm({ id: org.id, name: org.name, slug: org.slug })}>
                          Edit
                        </button>
                        <button type="button" className="admin-link-button" onClick={() => void toggleOrganization(org)}>
                          {org.is_active ? "Disable" : "Enable"}
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
    </div>
  );
}
