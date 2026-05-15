from app.domain.models import RevealedFact, RevealedFactPatch
from app.domain.public_facts import append_revealed_facts, is_probably_technical_value


def test_append_revealed_facts_filters_technical_values_and_deduplicates() -> None:
    existing = [RevealedFact(category="role", text="финансовый директор", turn_index=1)]
    updated = append_revealed_facts(
        existing,
        [
            RevealedFactPatch(category="role", text=" финансовый   директор "),
            RevealedFactPatch(category="role", text="cfo"),
            RevealedFactPatch(category="constraint", text="current_vendor_loyalty"),
            RevealedFactPatch(category="pain", text="Отчётность собирается вручную"),
        ],
        turn_index=2,
    )

    assert updated == [
        RevealedFact(category="role", text="финансовый директор", turn_index=1),
        RevealedFact(category="pain", text="Отчётность собирается вручную", turn_index=2),
    ]


def test_is_probably_technical_value_rejects_code_like_values() -> None:
    assert is_probably_technical_value("cfo")
    assert is_probably_technical_value("final_decider")
    assert is_probably_technical_value("current_vendor_loyalty")
    assert not is_probably_technical_value("финансовый директор")
