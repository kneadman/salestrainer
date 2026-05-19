import { useEffect, useState } from "react";
import { getTeamUserDetail, getTeamUsers } from "./api";
import { ClientBadge, ClientState, ClientStat } from "./components/ClientPrimitives";
import type { HistorySessionSummaryDTO, TeamUserDTO, TeamUserDetailDTO } from "./types";
import { buildClientHistorySessionViewModel, buildTeamUserViewModel } from "../viewModels";
import { getClientErrorMessage } from "./utils";

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
  return (
    <section className="client-panel">
      <div className="client-panel__header"><h1>Команда</h1></div>
      {users.length === 0 ? <ClientState title="Пользователей нет" /> : <TeamUsersTable users={users} onNavigate={onNavigate} />}
    </section>
  );
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

  const userVm = buildTeamUserViewModel(detail.user);
  return (
    <div className="client-page">
      <div className="client-page__header">
        <div>
          <a href="/app/team" className="client-link-button" onClick={(event) => { event.preventDefault(); onNavigate("/app/team"); }}>← Команда</a>
          <h1>{detail.user.email}</h1>
          <p>{userVm.roleLabel}</p>
        </div>
      </div>
      <section className="client-stats-grid">
        <ClientStat label="Всего" value={detail.analytics.total_sessions} />
        <ClientStat label="Завершено" value={detail.analytics.finished_sessions} />
        <ClientStat label="Средний интерес" value={detail.analytics.avg_final_interest_score?.toFixed(1) ?? "—"} />
        <ClientStat label="Среднее число ходов" value={detail.analytics.avg_turn_count?.toFixed(1) ?? "—"} />
      </section>
      <TeamUserDetailHistory history={detail.history} />
    </div>
  );
}

function TeamUsersTable({ users, onNavigate }: { users: TeamUserDTO[]; onNavigate: (path: string) => void }) {
  /** Render team users in a readable table for client leads. */
  const vms = users.map(buildTeamUserViewModel);
  return (
    <div className="client-table-wrap">
      <table className="client-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Роль</th>
            <th>Статус</th>
            <th>Тренировки</th>
            <th>Средний интерес</th>
            <th>Активность</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {vms.map((vm, index) => (
            <tr key={vm.id}>
              <td>{vm.email}</td>
              <td>{vm.roleLabel}</td>
              <td>
                <ClientBadge tone={vm.statusTone}>{vm.statusLabel}</ClientBadge>
              </td>
              <td>{users[index].finished_sessions}/{users[index].total_sessions}</td>
              <td>{users[index].avg_final_interest_score?.toFixed(1) ?? "—"}</td>
              <td>{users[index].last_activity_at ? new Date(users[index].last_activity_at).toLocaleDateString("ru-RU") : "—"}</td>
              <td>
                <a href={`/app/team/${vm.id}`} className="client-link-button" onClick={(event) => { event.preventDefault(); onNavigate(`/app/team/${vm.id}`); }}>
                  Открыть
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TeamUserDetailHistory({ history }: { history: HistorySessionSummaryDTO[] }) {
  /** Render one user's recent training history. */
  const vms = history.map(buildClientHistorySessionViewModel);
  return (
    <section className="client-panel">
      <h2>Последние тренировки</h2>
      {history.length === 0 ? (
        <ClientState title="Истории нет" />
      ) : (
        <div className="client-table-wrap">
          <table className="client-table">
            <thead>
              <tr><th>Дата</th><th>Статус</th><th>Сценарий</th><th>Интерес</th></tr>
            </thead>
            <tbody>
              {vms.map((vm) => (
                <tr key={vm.sessionId}>
                  <td>{vm.startedAtLabel}</td>
                  <td>{vm.statusLabel}</td>
                  <td>{vm.scenarioLabel}</td>
                  <td>{vm.finalInterestScore}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
