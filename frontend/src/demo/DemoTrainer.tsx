import { useMemo, useState } from "react";
import { ChatWindow } from "../components/ChatWindow";
import { Composer } from "../components/Composer";
import { SessionHeader } from "../components/SessionHeader";
import { TrainerContextPanel } from "../components/TrainerContextPanel";
import { TrainerStartScreen } from "../components/TrainerStartScreen";
import { TrainingReportModal } from "../components/TrainingReportModal";
import type { ClientStatePublic, JudgeSessionOutputDTO, SessionPublicDTO, TurnPublicDTO } from "../types";

type DemoTurn = {
  manager: string;
  client: string;
  metrics: { interest: number; trust: number; tone: string; band: string };
  facts?: Partial<ClientStatePublic>;
};

const DEMO_TURNS: DemoTurn[] = [
  {
    manager: "Привет! Расскажите, пожалуйста, какова ваша роль в компании?",
    client: "Я руководитель отдела маркетинга. Отвечаю за стратегию, бюджет и взаимодействие с подрядчиками.",
    metrics: { interest: 30, trust: 20, tone: "neutral", band: "neutral" },
    facts: { discovered_role: "руководитель отдела маркетинга" },
  },
  {
    manager: "Понял, спасибо. А вы единолично принимаете решения по внешним подрядчикам или нужно согласование?",
    client: "Финальное решение за мной, но для крупных контрактов я обсуждаю с CFO. С мелкими — сам решаю.",
    metrics: { interest: 35, trust: 25, tone: "neutral", band: "neutral" },
    facts: { discovered_authority_level: "принимает решения самостоятельно, крупные — с CFO" },
  },
  {
    manager: "Понятно. Расскажите, как сейчас организован процесс подготовки отчётности по рекламным кампаниям?",
    client: "Сейчас мы ведём всё в Google-таблицах. Бухгалтер собирает данные вручную из кабинетов, это занимает 3–4 дня в месяц.",
    metrics: { interest: 40, trust: 30, tone: "neutral", band: "warm" },
    facts: { discovered_current_process: ["ручной сбор в таблицах", "3–4 дня в месяц на отчётность"] },
  },
  {
    manager: "То есть основная нагрузка ложится на бухгалтера и ручной перенос данных?",
    client: "Да. Плюс постоянные переспросы из других отделов. Много времени уходит на согласование цифр и исправление ошибок.",
    metrics: { interest: 42, trust: 32, tone: "neutral", band: "warm" },
    facts: { discovered_current_process: ["переспросы из других отделов", "время на согласование и исправление ошибок"] },
  },
  {
    manager: "А какие главные сложности вы испытываете с текущим подходом?",
    client: "Главное — ошибки при ручном переносе и задержки. Из-за этого мы не успеваем корректировать бюджет вовремя и теряем эффективность.",
    metrics: { interest: 45, trust: 35, tone: "interested", band: "warm" },
    facts: { known_pains: ["ошибки при ручном переносе", "задержки и потеря эффективности бюджета"] },
  },
  {
    manager: "Задержки влияют на принятие решений по бюджету. Есть ли ещё что-то, что раздражает вас или команду?",
    client: "Да, отсутствие единого формата отчётов. Каждый раз приходится переделывать под разные запросы руководства и инвесторов.",
    metrics: { interest: 48, trust: 38, tone: "interested", band: "warm" },
    facts: { known_pains: ["отсутствие единого формата отчётов", "переделки под разные запросы"] },
  },
  {
    manager: "Понимаю. Когда вы рассматривали подрядчиков ранее, на что обращали внимание в первую очередь?",
    client: "На скорость и прозрачность. Хотим видеть цифры в реальном времени, без долгих сверок и уточнений.",
    metrics: { interest: 52, trust: 42, tone: "interested", band: "warm" },
    facts: { discovered_decision_criteria: ["скорость получения отчётов", "прозрачность без долгих сверок"] },
  },
  {
    manager: "То есть скорость и прозрачность — ключевые критерии. А как насчёт опыта в вашей отрасли?",
    client: "Это важно, но не критично. Главное — чтобы подрядчик понимал специфику рекламы и мог интегрироваться с нашими системами.",
    metrics: { interest: 55, trust: 45, tone: "interested", band: "warm" },
    facts: { discovered_decision_criteria: ["понимание специфики рекламы", "возможность интеграции с текущими системами"] },
  },
  {
    manager: "Есть ли у вас оценка бюджета на такую услугу или рамки, в которых вы хотели бы уложиться?",
    client: "Пока сложно сказать точно. Мы готовы обсуждать, если видим чёткую экономию времени и снижение ошибок.",
    metrics: { interest: 58, trust: 48, tone: "interested", band: "warm" },
    facts: { discovered_constraints: ["бюджет пока не определён", "готовы обсуждать при чёткой экономии"] },
  },
  {
    manager: "Какие сроки вы закладываете на внедрение и первые результаты?",
    client: "Хотелось бы запуститься до конца квартала, чтобы закрыть годовую отчётность без суеты и ручных доработок.",
    metrics: { interest: 62, trust: 50, tone: "warm", band: "hot" },
    facts: { discovered_constraints: ["внедрение до конца квартала", "закрытие годовой отчётности без доработок"] },
  },
  {
    manager: "До конца квартала — значит, около двух месяцев. Если мы сможем показать экономию в 30% времени, это было бы интересно?",
    client: "Да, это звучит привлекательно. Особенно если есть кейсы из маркетинга или смежных отраслей.",
    metrics: { interest: 68, trust: 55, tone: "warm", band: "hot" },
    facts: { buying_signals: ["интерес к экономии 30% времени", "хочет увидеть кейсы из маркетинга"] },
  },
  {
    manager: "У нас есть подобные кейсы. Как вы обычно работаете с возражениями по стоимости — это часто встречается?",
    client: "Цена всегда важна, но если модель прозрачная и есть понятный ROI, мы готовы платить за результат, а не за часы.",
    metrics: { interest: 70, trust: 58, tone: "warm", band: "hot" },
    facts: { visible_objections: ["ценность должна превосходить стоимость"] },
  },
  {
    manager: "Отлично, сфокусируемся на ROI. Давайте я подготовлю короткую презентацию с цифрами по вашему кейсу. Когда вам удобно созвониться на 20 минут?",
    client: "Давайте на следующей неделе, во вторник или среду после 14:00. Я приглашу CFO.",
    metrics: { interest: 75, trust: 62, tone: "ready_next_step", band: "hot" },
    facts: { discovered_authority_level: "CFO присоединится к созвону" },
  },
  {
    manager: "Зафиксируем среду в 15:00. Кто ещё должен присутствовать на созвоне из вашей стороны?",
    client: "Приглашу бухгалтера и аналитика. Им важно посмотреть, как будут выгружаться данные из кабинетов.",
    metrics: { interest: 78, trust: 65, tone: "ready_next_step", band: "hot" },
    facts: { discovered_current_process: ["бухгалтер и аналитик присоединятся к созвону", "важна выгрузка данных из кабинетов"] },
  },
  {
    manager: "Прекрасно, CFO и команда на созвоне — это важно. Я пришлю приглашение и короткий бриф до встречи. Спасибо за разговор!",
    client: "Спасибо вам! Буду ждать материалы. До встречи в среду.",
    metrics: { interest: 82, trust: 68, tone: "ready_next_step", band: "hot" },
    facts: { buying_signals: ["ожидает материалы", "подтверждён созвон в среду"] },
  },
];

const demoReportText =
  "Отличная работа! Вы выявили роль, текущий процесс и критерии принятия решения. Клиент проявил высокий уровень интереса (82/100) и доверия (68/100). Рекомендуем уточнить бюджет и сроки на созвоне с CFO.";

const demoReportPayload: JudgeSessionOutputDTO = {
  schema_version: 1,
  overall_score: 76,
  overall_grade: "good",
  outcome: "Позитивный",
  executive_summary:
    "Отличная работа! Вы выявили роль, текущий процесс и критерии принятия решения. Клиент проявил высокий уровень интереса (82/100) и доверия (68/100). Рекомендуем уточнить бюджет и сроки на созвоне с CFO.",
  bento_blocks: [
    {
      id: "b1",
      title: "Общее впечатление",
      type: "summary",
      severity: "green",
      score: null,
      short_text: "Диалог выстроен вокруг discovery-вопросов.",
      detail: "Менеджер последовательно выявил роль, процесс, боли и критерии.",
      evidence_turn_indexes: [1, 3, 5, 7],
    },
    {
      id: "b2",
      title: "Выявление потребностей",
      type: "score",
      severity: "green",
      score: 82,
      short_text: "Сильная сторона.",
      detail: "Заданы вопросы о текущем процессе, болях и критериях.",
      evidence_turn_indexes: [3, 5, 7],
    },
    {
      id: "b3",
      title: "Работа с возражениями",
      type: "score",
      severity: "yellow",
      score: 62,
      short_text: "Есть потенциал.",
      detail: "Возражение о цене было услышано, но не полностью раскрыто.",
      evidence_turn_indexes: [12],
    },
    {
      id: "b4",
      title: "Следующий шаг",
      type: "next_step",
      severity: "green",
      score: null,
      short_text: "Клиент готов к встрече.",
      detail: "Достигнута договоренность о следующем созвоне с CFO.",
      evidence_turn_indexes: [15],
    },
  ],
  skill_scores: [
    {
      id: "s1",
      title: "Выявление роли и полномочий",
      score: 88,
      severity: "green",
      explanation: "Роль и уровень влияния установлены на раннем этапе.",
      evidence_turn_indexes: [1, 2],
    },
    {
      id: "s2",
      title: "Discovery-вопросы",
      score: 85,
      severity: "green",
      explanation: "Процесс, боли и критерии выявлены последовательно.",
      evidence_turn_indexes: [3, 5, 7],
    },
    {
      id: "s3",
      title: "Презентация ценности",
      score: 70,
      severity: "yellow",
      explanation: "Ценность была привязана к ситуации, но можно глубже.",
      evidence_turn_indexes: [9, 11],
    },
    {
      id: "s4",
      title: "Закрытие следующего шага",
      score: 78,
      severity: "green",
      explanation: "Договоренность о следующем шаге получена.",
      evidence_turn_indexes: [15],
    },
  ],
  key_strengths: [
    {
      title: "Структурированный диалог",
      description: "Менеджер не спешил с предложением, а сначала изучил ситуацию.",
      evidence_turn_indexes: [1, 3, 5],
      impact: "high",
    },
  ],
  key_weaknesses: [
    {
      title: "Мало внимания бюджету",
      description: "Не уточнены финансовые рамки и сроки принятия решения.",
      evidence_turn_indexes: [9],
      impact: "medium",
    },
  ],
  missed_opportunities: [
    {
      title: "Не выявлены скрытые боли команды",
      description: "Можно было спросить, как текущий процесс влияет на подчинённых.",
      evidence_turn_indexes: [],
      impact: "medium",
    },
  ],
  recommendations: [
    {
      title: "Уточняйте бюджет раньше",
      description: "Понимание бюджета помогает подобрать решение.",
      example_phrase: "Какой бюджет вы закладываете на это направление в этом квартале?",
      priority: "high",
    },
    {
      title: "Сроки принятия решения",
      description: "Узнайте, когда планируется финальное решение.",
      example_phrase: "К какому сроку вам нужно понимать, подходит ли наше решение?",
      priority: "medium",
    },
  ],
  final_verdict: "Диалог завершён успешно. Менеджер продемонстрировал discovery-first подход.",
  risk_flags: [],
};

function mergeFacts(current: ClientStatePublic, next: Partial<ClientStatePublic>): ClientStatePublic {
  /** Accumulate array-valued facts and overwrite scalar facts. */
  const merged: ClientStatePublic = { ...current };
  if (next.discovered_role) merged.discovered_role = next.discovered_role;
  if (next.discovered_authority_level) merged.discovered_authority_level = next.discovered_authority_level;
  if (next.tone) merged.tone = next.tone;
  if (typeof next.trust === "number") merged.trust = next.trust;

  const arrayKeys: (keyof ClientStatePublic)[] = [
    "visible_objections",
    "known_pains",
    "buying_signals",
    "discovered_decision_criteria",
    "discovered_constraints",
    "discovered_current_process",
  ];

  for (const key of arrayKeys) {
    const nextArr = next[key] as string[] | undefined;
    if (nextArr && nextArr.length > 0) {
      const currentArr = (merged[key] as string[] | undefined) ?? [];
      (merged as unknown as Record<string, string[]>)[key] = [...currentArr, ...nextArr];
    }
  }

  return merged;
}

function buildSession(metrics: DemoTurn["metrics"], turnCount: number, clientState: ClientStatePublic): SessionPublicDTO {
  return {
    session_id: "demo-session",
    scenario_id: "generic_b2b_first_contact",
    status: "active",
    public_brief:
      "Вы — менеджер по продажам B2B-решений. Клиент: руководитель отдела маркетинга в средней компании. Ваша задача — провести discovery, выявить процесс, боли, критерии и договориться о следующем шаге.",
    stage: turnCount < 5 ? "discovery" : turnCount < 12 ? "qualification" : "next_step",
    interest: { score: metrics.interest, band: metrics.band },
    client_state_public: clientState,
    turn_count: turnCount,
    summary: "",
    state_version: 1,
  };
}

export function DemoTrainer() {
  /** Render a fully client-side demo trainer with a preset 15-turn dialogue. */
  const [started, setStarted] = useState(false);
  const [turnIndex, setTurnIndex] = useState(0);
  const [turns, setTurns] = useState<TurnPublicDTO[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [clientState, setClientState] = useState<ClientStatePublic>({});
  const [sessionMetrics, setSessionMetrics] = useState<SessionPublicDTO>(() =>
    buildSession({ interest: 0, trust: 0, tone: "neutral", band: "cold" }, 0, {})
  );
  const [hint, setHint] = useState("Нажмите «Начать тренировку», чтобы запустить демо");
  const [loading, setLoading] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [finished, setFinished] = useState(false);

  const factsState = useMemo(() => clientState, [clientState]);

  const handleStart = () => {
    setStarted(true);
    setTurnIndex(0);
    setTurns([]);
    setClientState({});
    setInputValue(DEMO_TURNS[0].manager);
    setFinished(false);
    setReportModalOpen(false);
    setSessionMetrics(buildSession({ interest: 0, trust: 0, tone: "neutral", band: "cold" }, 0, {}));
    setHint("Нажмите «Отправить», чтобы отправить первый ответ менеджера");
  };

  const handleSend = () => {
    if (!started || finished || loading || turnIndex >= DEMO_TURNS.length) {
      return;
    }

    const demoTurn = DEMO_TURNS[turnIndex];
    setLoading(true);
    setInputValue("");
    setHint("");

    setTimeout(() => {
      const newTurn: TurnPublicDTO = {
        turn_index: turnIndex,
        manager_message: demoTurn.manager,
        client_answer: demoTurn.client,
        interest_before: turnIndex === 0 ? 0 : DEMO_TURNS[turnIndex - 1].metrics.interest,
        interest_delta: demoTurn.metrics.interest - (turnIndex === 0 ? 0 : DEMO_TURNS[turnIndex - 1].metrics.interest),
        interest_after: demoTurn.metrics.interest,
        stage_before: "",
        stage_after: "",
        created_at: new Date().toISOString(),
      };

      const nextClientState = mergeFacts(clientState, {
        ...demoTurn.facts,
        tone: demoTurn.metrics.tone,
        trust: demoTurn.metrics.trust,
      });

      const nextSession = buildSession(demoTurn.metrics, turnIndex + 1, nextClientState);

      setTurns((prev) => [...prev, newTurn]);
      setClientState(nextClientState);
      setSessionMetrics(nextSession);
      setLoading(false);

      const nextIndex = turnIndex + 1;
      setTurnIndex(nextIndex);

      if (nextIndex >= DEMO_TURNS.length) {
        setFinished(true);
        setHint("Диалог завершён. Просмотрите отчёт");
      } else {
        setHint("Нажмите «Отправить», чтобы отправить следующий ответ менеджера");
        setInputValue(DEMO_TURNS[nextIndex].manager);
      }
    }, 700);
  };

  const handleFinish = () => {
    if (!started || finished || loading) {
      return;
    }
    setFinished(true);
    setReportModalOpen(true);
    setHint("Диалог завершён. Просмотрите отчёт");
  };

  const handleNewSession = () => {
    handleStart();
  };

  const isSending = loading;
  const canSend = started && !finished && !loading;
  const voiceDisabled = true;

  if (!started) {
    return (
      <TrainerStartScreen
        kicker="Демо-тренажёр"
        title="Попробуйте демо-тренировку"
        description="Пройдите предзаписанный discovery-диалог на 15 ходов и посмотрите, как работают метрики, факты и итоговый отчёт."
        hint={hint}
        buttonLabel="Начать демо-тренировку"
        onStart={handleStart}
        variant="demo"
      />
    );
  }

  return (
    <>
      <main className="client-trainer-layout">
        <aside className="trainer-side-panels trainer-side-panels--desktop" aria-label="Метрики и факты тренировки">
          <TrainerContextPanel session={sessionMetrics} factsState={factsState} mode="desktop" />
        </aside>
        <section className="trainer-chat-area" aria-label="Диалог тренировки">
          <section className="trainer-chat-panel">
            <SessionHeader
              busy={loading}
              canFinish={started && !finished}
              onNewSession={handleNewSession}
              onFinish={handleFinish}
              canShowReport={finished}
              onOpenReport={() => setReportModalOpen(true)}
            />
            <div className="trainer-context-slot trainer-context-slot--mobile">
              <TrainerContextPanel session={sessionMetrics} factsState={factsState} mode="mobile" />
            </div>
            <div className="trainer-chat-body">
              <ChatWindow turns={turns} loading={isSending} publicBrief={sessionMetrics.public_brief} />
            </div>
            {!finished ? (
              <>
                <Composer
                  value={inputValue}
                  onChange={setInputValue}
                  onSend={handleSend}
                  disabled={!canSend}
                  loading={isSending}
                  voiceDisabled={voiceDisabled}
                />
                {hint ? <p className="trainer-hint">{hint}</p> : null}
              </>
            ) : (
              <div className="composer">
                <p className="trainer-hint trainer-hint--finished">
                  {hint}
                </p>
              </div>
            )}
          </section>
        </section>
      </main>
      <TrainingReportModal
        open={reportModalOpen}
        report={demoReportText}
        reportPayload={demoReportPayload}
        onClose={() => setReportModalOpen(false)}
      />
    </>
  );
}
