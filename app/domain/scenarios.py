from __future__ import annotations

from app.domain.errors import UnknownScenarioError
from app.domain.models import Scenario


SCENARIOS: dict[str, Scenario] = {
    "sales_audit_cold_outreach": Scenario(
        id="sales_audit_cold_outreach",
        name="Cold outreach for sales audit",
        offer="Audit, corrections, and control of the sales department",
        target_audience="Owners and leaders of B2B companies",
        default_starting_interest=25,
        default_stage="first_contact",
        success_condition="Client agrees to a diagnostic call or to share input data.",
        failure_condition="Client clearly refuses to continue the dialogue.",
    ),
    "accounting_outsource_cold_outreach": Scenario(
        id="accounting_outsource_cold_outreach",
        name="Cold outreach for accounting outsourcing",
        offer="Transfer accounting operations to an outsource provider",
        target_audience="Owners, directors, and finance leaders",
        default_starting_interest=20,
        default_stage="first_contact",
        success_condition="Client agrees to discuss a review or pricing estimate.",
        failure_condition="Client refuses and leaves no open questions.",
    ),
}


def list_scenarios() -> list[Scenario]:
    return list(SCENARIOS.values())


def get_scenario(scenario_id: str) -> Scenario:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as error:
        raise UnknownScenarioError(f"Unknown scenario_id '{scenario_id}'.") from error
