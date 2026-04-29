from __future__ import annotations

from app.domain.models import ClientState, PersonaProfile, TurnEvaluation


ROLE_TOKENS = ["кто вы", "ваша роль", "за что отвечаете", "кто принимает решение", "кто согласует"]
PAIN_TOKENS = ["какая проблема", "что болит", "где потери", "воронка", "продажи", "бухгалтерия", "финансы", "заявки", "лиды"]
PRESSURE_TOKENS = ["купите", "срочно", "только сегодня", "давайте сразу", "встреча завтра", "подпишем"]
RELEVANCE_TOKENS = ["контроль", "окупаем", "окупаемость", "результат", "процесс", "конвер", "потер", "цифр"]
NEXT_STEP_TOKENS = ["следующий шаг", "созвон", "встреч", "диагностик", "аудит"]
OBJECTION_TOKENS = ["понимаю", "если я правильно понял", "правильно ли", "что мешает", "из-за чего"]


def evaluate_turn(
    *,
    turn_index: int,
    manager_message: str,
    client_state: ClientState,
    hidden_profile: PersonaProfile,
) -> TurnEvaluation:
    text = manager_message.lower()
    asks_question = "?" in text
    role_score = 5 if any(token in text for token in ROLE_TOKENS) else 1 if asks_question else 0
    pain_score = 5 if any(token in text for token in PAIN_TOKENS) else 1 if asks_question else 0
    discovery_score = min(5, role_score + pain_score if asks_question else max(role_score, pain_score))
    relevance_score = 4 if any(token in text for token in RELEVANCE_TOKENS) else 2 if asks_question else 1
    pressure_score = 0 if any(token in text for token in PRESSURE_TOKENS) else 5
    objection_score = 4 if any(token in text for token in OBJECTION_TOKENS) else 2 if client_state.open_objections else 1
    next_step_early = (
        any(token in text for token in NEXT_STEP_TOKENS)
        and (client_state.discovered_role is None or not client_state.discovered_pains)
    )
    next_step_score = 1 if next_step_early else 4 if any(token in text for token in NEXT_STEP_TOKENS) else 3
    control_score = 4 if asks_question else 2

    notes: list[str] = []
    if role_score >= 5:
        notes.append("Manager tried to identify the client's role or authority.")
    if pain_score >= 5:
        notes.append("Manager probed for business pain or process issues.")
    if any(token in text for token in PRESSURE_TOKENS):
        notes.append("Manager applied pressure too early.")
    if next_step_early:
        notes.append("Manager pushed for a next step before enough discovery.")
    if hidden_profile.role in text:
        notes.append("Manager referenced the client's role explicitly.")

    return TurnEvaluation(
        turn_index=turn_index,
        discovery_quality_score=max(0, min(5, discovery_score)),
        role_identification_score=max(0, min(5, role_score)),
        pain_identification_score=max(0, min(5, pain_score)),
        relevance_score=max(0, min(5, relevance_score)),
        pressure_score=max(0, min(5, pressure_score)),
        objection_handling_score=max(0, min(5, objection_score)),
        next_step_timing_score=max(0, min(5, next_step_score)),
        conversation_control_score=max(0, min(5, control_score)),
        notes=notes,
    )
