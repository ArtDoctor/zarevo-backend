from pathlib import Path

import chromadb
from pydantic import BaseModel


class IndustryRaw(BaseModel):
    sector: str
    name: str
    sizes: list[int]


class MarketEntry(BaseModel):
    name: str
    sector: str
    growth_rate: str
    sizes_2023_2026_in_millions: list[int]


class MarketAnalysis(BaseModel):
    overview: str
    trends_analysis: str
    markets: list[MarketEntry]
    sectors: list[str]
    average_growth_rate: str
    strengths: list[str]
    weaknesses: list[str]
    gaps_and_opportunities: list[str]
    threats: list[str]
    new_market_potential: str
    why_now: str
    score: int


def _growth_rate_from_sizes(sizes: list[int]) -> str:
    if not sizes or sizes[0] == 0:
        return "0%"
    rate = ((sizes[-1] - sizes[0]) / sizes[0]) * 100
    return f"{rate:.1f}%"


def _get_collection() -> chromadb.Collection:
    data_dir = Path(__file__).parent / ".chroma_data"
    data_dir.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(data_dir))
    return client.get_or_create_collection("industries", metadata={"hnsw:space": "cosine"})


def _ensure_industries_indexed(collection: chromadb.Collection) -> list[IndustryRaw]:
    industries_path = Path(__file__).parent / "industries.json"
    industries: list[IndustryRaw] = [
        IndustryRaw.model_validate(item) for item in _load_json(industries_path)
    ]
    if collection.count() > 0:
        return industries
    documents = [f"{ind.sector} {ind.name}" for ind in industries]
    metadatas = [{"idx": i} for i in range(len(industries))]
    ids = [str(i) for i in range(len(industries))]
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return industries


def _load_json(path: Path) -> list[dict]:
    import json

    return json.loads(path.read_text())


def _search_markets(description: str, top_k: int = 5) -> list[MarketEntry]:
    collection = _get_collection()
    industries = _ensure_industries_indexed(collection)
    results = collection.query(query_texts=[description], n_results=min(top_k, len(industries)))
    if not results or not results["ids"] or not results["ids"][0]:
        return []
    indices = [int(idx) for idx in results["ids"][0]]
    entries: list[MarketEntry] = []
    for idx in indices:
        ind = industries[idx]
        growth = _growth_rate_from_sizes(ind.sizes)
        entries.append(
            MarketEntry(
                name=ind.name,
                sector=ind.sector,
                growth_rate=growth,
                sizes_2023_2026_in_millions=ind.sizes,
            )
        )
    return entries


def get_market_analysis(idea: dict) -> MarketAnalysis:
    from src.config import IdeaRequest

    validated = IdeaRequest.model_validate(idea)
    description = validated.description
    if validated.problem:
        description = f"{description} {validated.problem}"
    if validated.customer:
        description = f"{description} {validated.customer}"

    markets = _search_markets(description, top_k=5)
    sectors = list(dict.fromkeys(m.sector for m in markets))

    avg_growth = "0%"
    if markets:
        rates = []
        for m in markets:
            s = m.sizes_2023_2026_in_millions
            if s and s[0] != 0:
                rates.append(((s[-1] - s[0]) / s[0]) * 100)
        avg_growth = f"{sum(rates) / len(rates):.1f}%" if rates else "0%"

    return MarketAnalysis(
        overview="",
        trends_analysis="",
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
        strengths=[],
        weaknesses=[],
        gaps_and_opportunities=[],
        threats=[],
        new_market_potential="",
        why_now="",
        score=0,
    )
