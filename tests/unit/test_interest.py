from app.domain.interest import apply_interest_delta, interest_band


def test_apply_interest_delta_clamps_upper_bound() -> None:
    assert apply_interest_delta(95, 15) == 100


def test_apply_interest_delta_clamps_lower_bound() -> None:
    assert apply_interest_delta(5, -15) == 0


def test_interest_band_boundaries() -> None:
    assert interest_band(20) == "cold"
    assert interest_band(21) == "skeptical"
    assert interest_band(40) == "skeptical"
    assert interest_band(41) == "neutral"
    assert interest_band(60) == "neutral"
    assert interest_band(61) == "warm"
    assert interest_band(80) == "warm"
    assert interest_band(81) == "hot"

