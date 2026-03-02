from src.analyses.market.market import (
    MarketAnalysis,
    MarketEntry,
    get_market_analysis,
)


def test_market_vector_search_returns_healthcare_industries_for_healthcare_idea() -> None:
    idea = {
        "description": "SaaS for healthcare providers to manage patient records and telemedicine",
        "problem": "",
        "customer": "",
        "geography": "",
        "founder_specific": "",
    }
    result = get_market_analysis(idea)

    assert isinstance(result, MarketAnalysis)
    assert len(result.markets) == 5
    assert all(m.sector == "Health Care" for m in result.markets)
    assert result.sectors == ["Health Care"]
    assert "Health Care" in result.sectors

    for market in result.markets:
        assert isinstance(market, MarketEntry)
        assert market.name
        assert market.sector
        assert market.growth_rate.endswith("%")
        assert len(market.sizes_2023_2026_in_millions) == 4

    assert result.average_growth_rate.endswith("%")


def test_market_vector_search_returns_relevant_industries_for_fintech_idea() -> None:
    idea = {
        "description": "Payment processing and lending software for small businesses",
        "problem": "",
        "customer": "",
        "geography": "",
        "founder_specific": "",
    }
    result = get_market_analysis(idea)

    assert len(result.markets) == 5
    assert len(result.sectors) >= 1
    assert all(m.sector in result.sectors for m in result.markets)
