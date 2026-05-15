from app.prompts.schemas import load_client_simulator_prompt


def test_client_simulator_prompt_uses_universal_revealed_facts_contract() -> None:
    prompt = load_client_simulator_prompt()

    assert "accounting outsourcing" not in prompt
    assert "outsourced CFO services" not in prompt
    assert "revealed_facts" in prompt
    assert "`revealed_facts` НЕ является частью `state_patch`" in prompt
    assert "Запрещены технические коды" in prompt
