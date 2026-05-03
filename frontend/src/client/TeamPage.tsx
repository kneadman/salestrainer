import { useEffect, useState } from "react";
import { getTeamUserDetail, getTeamUsers } from "./api";
import { ClientBadge, ClientState, ClientStat } from "./components/ClientPrimitives";
import type { TeamUserDTO, TeamUserDetailDTO } from "./types";
import { formatClientDate, getClientErrorMessage } from "./utils";

type TeamPageProps = {
  userId?: string;
  onNavigate: (path: string) => void;
};

export function TeamPage({ userId, onNavigate }: TeamPageProps) {
  /** Route team list and team user detail for client leads. */
  if (userId) {
    return <TeamUserDetail userId={userId} onNavigate={onNavigate} />;
  }
  return <TeamList onNavigate={onNavigate} />;
}

function TeamList({ onNavigate }: { onNavigate: (path: string) => void }) {
  /** Render same-organization team users for client leads. */
  const [users, setUsers] = useState<TeamUserDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Load team users from the safe client-facing endpoint. */
    const load = async () => {
      try {
        setUsers(await getTeamUsers());
      } catch (loadError) {
        setError(getClientErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return <ClientState title="Загрузка команды" />;
  }
  if (error) {
    return <ClientState title="Команда недоступна" detail={error} tone="error" />;
  }
  return <section className="client-panel"><div className="client-panel__header"><h1>Команда</h1></div>{users.length === 0 ? <ClientState title="Пользователей нет" /> : <div className="client-table-wrap"><table className="client-table"><thead><tr><th>Email</th><th>Роль</th><th>Статус</th><th>Тренировки</th><th>Avg interest</th><th>Активность</th><th></th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td>{user.email}</td><td>{user.role}</td><td><ClientBadge tone={user.is_active ? "good" : "danger"}>{user.is_active ? "active" : "disabled"}</ClientBadge>{user.must_change_password ? <ClientBadge tone="warning">password</ClientBadge> : null}</td><td>{user.finished_sessions}/{user.total_sessions}</td><td>{user.avg_final_interest_score?.toFixed(1) ?? "—"}</td><td>{formatClientDate(user.last_activity_at)}</td><td><button type="button" className="client-link-button" onClick={() => onNavigate(`/app/team/${user.id}`)}>Открыть</button></td></tr>)}</tbody></table></div>}</section>;
}

function TeamUserDetail({ userId, onNavigate }: { userId: string; onNavigate: (path: string) => void }) {
  /** Render one same-organization manager card for client leads. */
  const [detail, setDetail] = useState<TeamUserDetailDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Load manager detail analytics from the team endpoint. */
    const load = async () => {
      try {
        setDetail(await getTeamUserDetail(userId));
      } catch (loadError) {
        setError(getClientErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [userId]);

  if (loading) {
    return <ClientState title="Загрузка менеджера" />;
  }
  if (error || !detail) {
    return <ClientState title="Менеджер недоступен" detail={error ?? "Не найден."} tone="error" />;
  }
  return <div className="client-page"><div className="client-page__header"><div><button type="button" className="client-link-button" onClick={() => onNavigate("/app/team")}>← Команда</button><h1>{detail.user.email}</h1><p>{detail.user.role}</p></div></div><section className="client-stats-grid"><ClientStat label="Всего" value={detail.analytics.total_sessions} /><ClientStat label="Завершено" value={detail.analytics.finished_sessions} /><ClientStat label="Avg interest" value={detail.analytics.avg_final_interest_score?.toFixed(1) ?? "—"} /><ClientStat label="Avg turns" value={detail.analytics.avg_turn_count?.toFixed(1) ?? "—"} /></section><section className="client-panel"><h2>Последние тренировки</h2>{detail.history.length === 0 ? <ClientState title="Истории нет" /> : <div className="client-table-wrap"><table className="client-table"><thead><tr><th>Дата</th><th>Статус</th><th>Сценарий</th><th>Interest</th></tr></thead><tbody>{detail.history.map((item) => <tr key={item.session_id}><td>{formatClientDate(item.started_at)}</td><td>{item.status}</td><td>{item.scenario_id}</td><td>{item.final_interest_score ?? "—"}</td></tr>)}</tbody></table></div>}</section></div>;
}
