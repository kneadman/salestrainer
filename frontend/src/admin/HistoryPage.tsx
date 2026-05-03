import { useEffect, useState } from "react";
import { getHistorySession, listOrganizationHistory, listOrganizations } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState } from "./components/AdminPrimitives";
import type { HistorySessionDetailDTO, HistorySessionSummaryDTO, OrganizationDTO } from "./types";
import { formatDate, getErrorMessage } from "./utils";

type HistoryPageProps = {
  sessionId?: string;
  onNavigate: (path: string) => void;
};

export function HistoryPage({ sessionId, onNavigate }: HistoryPageProps) {
  /** Route to either global history list or session detail depending on path state. */
  if (sessionId) {
    return <HistoryDetail sessionId={sessionId} onNavigate={onNavigate} />;
  }
  return <HistoryList onNavigate={onNavigate} />;
}

function HistoryList({ onNavigate }: { onNavigate: (path: string) => void }) {
  /** Load organization-scoped history for the selected organization filter. */
  const [organizations, setOrganizations] = useState<OrganizationDTO[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [status, setStatus] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [history, setHistory] = useState<HistorySessionSummaryDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async (selectedOrganizationId: string, selectedStatus = status, selectedScenarioId = scenarioId) => {
    /** Fetch history rows only when an organization is selected. */
    if (!selectedOrganizationId) {
      setHistory([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setHistory(await listOrganizationHistory(selectedOrganizationId, { status: selectedStatus, scenario_id: selectedScenarioId, limit: 100, offset: 0 }));
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    /** Bootstrap organizations and load history for the first organization when available. */
    const bootstrap = async () => {
      setLoading(true);
      setError(null);
      try {
        const orgs = await listOrganizations();
        setOrganizations(orgs);
        const firstId = orgs[0]?.id ?? "";
        setOrganizationId(firstId);
        await load(firstId, "", "");
      } catch (bootstrapError) {
        setError(getErrorMessage(bootstrapError));
        setLoading(false);
      }
    };
    void bootstrap();
  }, []);

  if (loading) {
    return <LoadingState title="Loading training history" />;
  }

  if (error) {
    return <ErrorState title="History unavailable" detail={error} />;
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header"><div><span className="admin-kicker">Persistent history</span><h1>Training History</h1></div></div>
      <section className="admin-panel">
        <form className="admin-form admin-form--inline" onSubmit={(event) => { event.preventDefault(); void load(organizationId); }}>
          <label><span>Organization</span><select value={organizationId} onChange={(event) => { setOrganizationId(event.target.value); void load(event.target.value); }}>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label>
          <label><span>Status</span><input value={status} onChange={(event) => setStatus(event.target.value)} placeholder="active / finished" /></label>
          <label><span>Scenario</span><input value={scenarioId} onChange={(event) => setScenarioId(event.target.value)} /></label>
          <button type="submit" className="admin-button admin-button--primary">Apply</button>
        </form>
      </section>
      <section className="admin-panel">
        {history.length === 0 ? <EmptyState title="No history rows" detail="No sessions match the selected filters." /> : (
          <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Session</th><th>User</th><th>Status</th><th>Scenario</th><th>Turns</th><th>Interest</th><th>Started</th><th>Actions</th></tr></thead><tbody>{history.map((session) => <tr key={session.session_id}><td>{session.session_id.slice(0, 8)}</td><td>{session.user_email}</td><td><Badge>{session.status}</Badge></td><td>{session.scenario_id}</td><td>{session.turn_count}</td><td>{session.final_interest_score ?? "—"}</td><td>{formatDate(session.started_at)}</td><td><button type="button" className="admin-link-button" onClick={() => onNavigate(`/admin/history/sessions/${session.session_id}`)}>Open</button></td></tr>)}</tbody></table></div>
        )}
      </section>
    </div>
  );
}

function HistoryDetail({ sessionId, onNavigate }: { sessionId: string; onNavigate: (path: string) => void }) {
  /** Load and render one public-safe persistent history session detail. */
  const [detail, setDetail] = useState<HistorySessionDetailDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Fetch session detail from the history API by id. */
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        setDetail(await getHistorySession(sessionId));
      } catch (loadError) {
        setError(getErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [sessionId]);

  if (loading) {
    return <LoadingState title="Loading session history" />;
  }

  if (error || !detail) {
    return <ErrorState title="Session history unavailable" detail={error ?? "Session not found."} />;
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header"><div><button type="button" className="admin-link-button" onClick={() => onNavigate("/admin/history")}>← History</button><h1>Session {detail.session.session_id.slice(0, 8)}</h1><p className="admin-muted">{detail.session.user_email} · {detail.session.scenario_id}</p></div><Badge>{detail.session.status}</Badge></div>
      <section className="admin-panel"><h2>Summary</h2><p>{detail.session.summary ?? "No summary."}</p><p className="admin-muted">{detail.public_brief ?? ""}</p></section>
      <section className="admin-panel"><h2>Turns</h2>{detail.turns.length === 0 ? <EmptyState title="No turns" /> : <div className="admin-history-turns">{detail.turns.map((turn) => <article key={turn.turn_index}><div><Badge>#{turn.turn_index}</Badge><span>{formatDate(turn.created_at)}</span></div><p><strong>Manager:</strong> {turn.manager_message}</p><p><strong>Client:</strong> {turn.client_answer}</p><p className="admin-muted">Interest {turn.interest_before} → {turn.interest_after}; stage {turn.stage_before} → {turn.stage_after}</p></article>)}</div>}</section>
      <section className="admin-panel"><h2>Report</h2>{detail.report ? <pre className="admin-report-block">{detail.report.report}</pre> : <EmptyState title="No saved report" />}</section>
    </div>
  );
}
