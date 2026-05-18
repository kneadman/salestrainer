from __future__ import annotations

from typing import Any

from app.domain.interest import interest_band
from app.domain.models import LLMTurnInput, LLMTurnResponse, RevealedFactPatch, StatePatch


class FakeLLMClient:
    ROLE_TOKENS = ["кто вы", "ваша роль", "за что отвечаете"]
    AUTHORITY_TOKENS = ["кто принимает решение", "кто согласует", "есть ли полномочия"]
    PAIN_TOKENS = ["какая проблема", "что болит", "болит", "где потери", "что мешает", "проблем"]
    ACCOUNTING_TOKENS = ["бухгалтер", "бухгалтерия", "учет", "учёт"]
    DECISION_CRITERIA_TOKENS = ["по каким критериям", "что важно", "как выбираете"]
    CONSTRAINT_TOKENS = ["что мешает", "какие ограничения", "риски"]
    PROCESS_TOKENS = [
        "как сейчас устроено",
        "как сейчас устроена",
        "что происходит",
        "как работает",
        "процесс",
        "воронка",
        "как ведется бухгалтерия",
        "как ведёте бухгалтерию",
        "чем занимаетесь",
        "чем занимается компания",
        "какой у вас бизнес",
    ]
    DIAGNOSTIC_TOKENS = [
        *ROLE_TOKENS,
        *PROCESS_TOKENS,
        *PAIN_TOKENS,
        *DECISION_CRITERIA_TOKENS,
        *CONSTRAINT_TOKENS,
        "продажи",
        "бухгалтерия",
        "финансы",
        "заявки",
        "лиды",
        "потери",
        "контроль",
        "diagnostic",
        "conversion",
        "funnel",
        "loss",
        "problem",
    ]

    @staticmethod
    def _contains_any(message_lower: str, tokens: list[str]) -> bool:
        return any(token in message_lower for token in tokens)

    def generate_client_turn(self, payload: LLMTurnInput) -> LLMTurnResponse:
        message = payload.manager_message.strip()
        message_lower = message.lower()
        profile = payload.hidden_profile
        discovered = payload.discovered_facts
        current_interest = int(payload.current_state["interest_score"])
        delta = self._score_message(message_lower, profile)
        next_interest = max(0, min(100, current_interest + delta))
        band = interest_band(next_interest)
        stage = self._choose_stage(
            message_lower,
            current_stage=str(payload.current_state["stage"]),
            next_interest=next_interest,
            discovered=discovered,
        )
        answer = self._build_answer(band, payload)
        patch = self._build_patch(message_lower, band, profile)
        revealed_facts = self._build_revealed_facts(message_lower, profile)
        notes = self._build_notes(delta, band, message)
        return LLMTurnResponse(
            answer=answer,
            interest_delta=delta,
            state_patch=patch,
            revealed_facts=revealed_facts,
            stage=stage,
            internal_notes=notes,
        )

    def _score_message(self, message_lower: str, profile: Any) -> int:
        score = 0
        if len(message_lower) < 12:
            score -= 4
        if "?" in message_lower:
            score += 4
        if self._contains_any(message_lower, self.DIAGNOSTIC_TOKENS):
            score += 3
        if self._contains_any(
            message_lower,
            ["you must", "buy", "urgent offer", "only today", "купите", "срочно", "только сегодня"],
        ):
            score -= 6
        if self._contains_any(
            message_lower,
            ["price", "cost", "roi", "result", "стоимость", "цена", "окупаемость", "результат"],
        ):
            score += 2
        if any(token in message_lower for token in profile.industry.lower().split("_")):
            score += 1
        return max(-15, min(15, score))

    def _choose_stage(self, message_lower: str, current_stage: str, next_interest: int, discovered: dict[str, Any]) -> str:
        if self._contains_any(message_lower, self.ROLE_TOKENS):
            return "role_discovery"
        if next_interest >= 75 and "?" in message_lower and discovered.get("role") and discovered.get("pains"):
            return "next_step_negotiation"
        if self._contains_any(message_lower, ["why", "how", "problem", "loss", "как", "почему", *self.PAIN_TOKENS]):
            return "need_discovery"
        if self._contains_any(
            message_lower,
            ["example", "result", "roi", "diagnostic", "результат", "окупаемость", "эффект"],
        ):
            return "value_clarification"
        return current_stage

    def _build_answer(self, band: str, payload: LLMTurnInput) -> str:
        profile = payload.hidden_profile
        discovered = payload.discovered_facts
        message_lower = payload.manager_message.lower()

        if self._contains_any(message_lower, self.ROLE_TOKENS):
            return self._role_answer(profile, discovered)
        if self._contains_any(message_lower, self.DECISION_CRITERIA_TOKENS):
            return f"Мне важно понять: {profile.decision_criteria[0]}."
        if self._contains_any(message_lower, self.CONSTRAINT_TOKENS):
            return profile.hidden_constraints[0]
        if self._contains_any(message_lower, self.PROCESS_TOKENS):
            return self._process_answer(profile)
        if self._contains_any(message_lower, self.PAIN_TOKENS):
            return profile.latent_pains[0]
        if self._contains_any(message_lower, self.AUTHORITY_TOKENS):
            return self._authority_answer(profile)
        if self._contains_any(message_lower, ["цена", "стоимость", "окупаемость", "результат"]):
            return "Сначала хочу понять, в чём конкретно для нас будет ценность."
        if band == "cold":
            return "Пока звучит слишком общо. Уточните, что именно вы хотите понять."
        if band == "skeptical":
            return "Сформулируйте короче и привяжите к нашей ситуации."
        if band == "neutral":
            return "Допустим. Какие данные вам обычно нужны, чтобы понять ситуацию?"
        if band == "warm":
            return "Уже ближе к делу. Если быстро поймёте контекст, что предложите как следующий шаг?"
        return "Ок. Тогда покажите, как вы обычно переводите это в конкретный следующий шаг."

    def _process_answer(self, profile: Any) -> str:
        parts = [profile.current_business_context]
        parts.append(f"Текущее решение: {profile.current_solution}.")
        parts.extend(profile.business_facts[:2])
        return " ".join(part.strip() for part in parts if part.strip())[:280]

    def _role_answer(self, profile: Any, discovered: dict[str, Any]) -> str:
        if discovered.get("role") in {profile.role, self._public_role_label(profile.role)}:
            return "Я уже сказал, что отвечаю за этот блок."
        answers = {
            "owner": "Я собственник, отвечаю за ключевые решения и финансовый результат.",
            "founder": "Я основатель компании, отвечаю за рост и управляемость бизнеса.",
            "ceo": "Я CEO, отвечаю за общий результат и ключевые управленческие решения.",
            "general_director": "Я генеральный директор, отвечаю за операционное управление и результат.",
            "managing_partner": "Я управляющий партнёр, отвечаю за развитие и качество управления.",
            "commercial_director": "Я коммерческий директор, отвечаю за продажи, маржу и выполнение плана.",
            "cfo": "Я финансовый директор, отвечаю за цифры, денежный поток и финансовую прозрачность.",
            "chief_accountant": "Я главный бухгалтер, отвечаю за учёт, отчётность и налоговые риски.",
            "operations_director": "Я операционный директор, отвечаю за процессы и устойчивость работы.",
            "sales_director": "Я руководитель отдела продаж, отвечаю за воронку, менеджеров и план.",
            "purchase_manager": "Я менеджер по закупкам, отвечаю за выбор подрядчиков и первичную оценку предложений.",
        }
        return answers.get(profile.role, "Я отвечаю за часть управленческих решений в компании.")

    def _authority_answer(self, profile: Any) -> str:
        return {
            "final_decider": "Финальное решение могу принять сам, если вижу смысл.",
            "influencer": "Я влияю на решение, но финально нужен ещё другой участник.",
            "gatekeeper": "Сначала мне нужно понять релевантность, потом могу передать дальше.",
            "evaluator": "Я оцениваю экономику и риски, финальное решение не только за мной.",
        }[profile.authority_level]

    def _build_revealed_facts(self, message_lower: str, profile: Any) -> list[RevealedFactPatch]:
        if self._contains_any(message_lower, self.ROLE_TOKENS):
            return [RevealedFactPatch(category="role", text=self._public_role_label(profile.role))]
        if self._contains_any(message_lower, self.DECISION_CRITERIA_TOKENS):
            return [RevealedFactPatch(category="decision_criterion", text=profile.decision_criteria[0])]
        if self._contains_any(message_lower, self.CONSTRAINT_TOKENS):
            return [RevealedFactPatch(category="constraint", text=profile.hidden_constraints[0])]
        if self._contains_any(message_lower, self.PROCESS_TOKENS):
            return [
                RevealedFactPatch(category="current_process", text=profile.current_business_context),
                RevealedFactPatch(category="current_process", text=f"Текущее решение: {profile.current_solution}."),
            ]
        if self._contains_any(message_lower, self.PAIN_TOKENS):
            return [RevealedFactPatch(category="pain", text=profile.latent_pains[0])]
        if self._contains_any(message_lower, self.AUTHORITY_TOKENS):
            return [RevealedFactPatch(category="authority", text="может принять финальное решение сам")]
        return []

    def _public_role_label(self, role: str) -> str:
        labels = {
            "owner": "собственник",
            "founder": "основатель компании",
            "ceo": "генеральный директор",
            "general_director": "генеральный директор",
            "managing_partner": "управляющий партнёр",
            "commercial_director": "коммерческий директор",
            "cfo": "финансовый директор",
            "chief_accountant": "главный бухгалтер",
            "operations_director": "операционный директор",
            "sales_director": "руководитель отдела продаж",
            "purchase_manager": "менеджер по закупкам",
        }
        return labels.get(role, "руководитель")

    def _build_patch(self, message_lower: str, band: str, profile: Any) -> StatePatch:
        add_open_objections: list[str] = []
        remove_open_objections: list[str] = []
        known_pains: list[str] = []
        buying_signals: list[str] = []
        red_flags: list[str] = []
        discovered_pains: list[str] = []
        decision_criteria: list[str] = []
        constraints: list[str] = []
        current_process: list[str] = []
        trust_delta = 0
        irritation_delta = 0
        urgency_delta = 0
        tone = None
        discovered_role = None
        discovered_authority_level = None

        if "?" in message_lower:
            trust_delta += 3
            irritation_delta -= 1
            known_pains.append("Manager asked a diagnostic question instead of generic pitching.")
        if self._contains_any(
            message_lower,
            ["conversion", "loss", "funnel", "diagnostic", "воронка", "потери", "как сейчас устроено", "как сейчас устроена"],
        ):
            trust_delta += 2
            urgency_delta += 1
            remove_open_objections.append("I do not see why this is necessary.")
        if self._contains_any(message_lower, ["buy", "must", "only today", "купите", "срочно", "только сегодня"]):
            irritation_delta += 4
            red_flags.append("Manager became pushy.")
        if self._contains_any(message_lower, self.ROLE_TOKENS):
            discovered_role = profile.role
            trust_delta += 2
        if self._contains_any(message_lower, self.AUTHORITY_TOKENS):
            discovered_authority_level = profile.authority_level
            trust_delta += 1
        if self._contains_any(message_lower, self.PAIN_TOKENS):
            discovered_pains.extend(profile.latent_pains[:1])
            known_pains.extend(profile.latent_pains[:1])
            trust_delta += 2
        if self._contains_any(message_lower, self.PROCESS_TOKENS):
            current_process.append(profile.current_business_context)
            current_process.append(f"Текущее решение: {profile.current_solution}.")
            current_process.extend(profile.business_facts[:2])
            if self._contains_any(message_lower, self.ACCOUNTING_TOKENS):
                current_process.append("Учет финансовых данных обсуждается как часть текущего процесса.")
        if self._contains_any(message_lower, self.DECISION_CRITERIA_TOKENS):
            decision_criteria.extend(profile.decision_criteria[:2])
        if self._contains_any(message_lower, self.CONSTRAINT_TOKENS):
            constraints.extend(profile.hidden_constraints[:1])

        if band in {"neutral", "warm", "hot"}:
            buying_signals.append("Client asked about scope, time, or next step.")
        if band == "cold":
            tone = "cold"
            add_open_objections.append("Still does not see enough relevance.")
        elif band == "skeptical":
            tone = "skeptical"
            add_open_objections.append("Needs more concrete proof and relevance.")
        elif band == "neutral":
            tone = "neutral"
        elif band == "warm":
            tone = "warm"
        else:
            tone = "ready_next_step"

        return StatePatch(
            tone=tone,
            trust_delta=max(-15, min(15, trust_delta)),
            irritation_delta=max(-15, min(15, irritation_delta)),
            urgency_delta=max(-15, min(15, urgency_delta)),
            add_open_objections=add_open_objections,
            remove_open_objections=remove_open_objections,
            add_known_pains=known_pains,
            add_buying_signals=buying_signals,
            add_red_flags=red_flags,
            set_discovered_role=discovered_role,
            set_discovered_authority_level=discovered_authority_level,
            add_discovered_pains=discovered_pains,
            add_discovered_decision_criteria=decision_criteria,
            add_discovered_constraints=constraints,
            add_discovered_current_process=current_process,
        )

    def _build_notes(self, delta: int, band: str, message: str) -> str:
        direction = "improved" if delta > 0 else "did not improve"
        return f"Client interest {direction}; resulting band is {band}. Manager message length={len(message)}."
