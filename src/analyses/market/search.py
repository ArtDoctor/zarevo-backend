import json
from pathlib import Path

import chromadb

from src.analyses.market.models import IndustryRaw, MarketEntry


def growth_rate_from_sizes(sizes: list[int]) -> str:
    if not sizes or sizes[0] == 0:
        return "0%"
    rate = ((sizes[-1] - sizes[0]) / sizes[0]) * 100
    return f"{rate:.1f}%"


def _get_collection() -> chromadb.Collection:
    data_dir = Path(__file__).parent / ".chroma_data"
    data_dir.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(data_dir))
    return client.get_or_create_collection("industries", metadata={"hnsw:space": "cosine"})


def _load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text())


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


def search_markets(description: str, top_k: int = 5) -> list[MarketEntry]:
    collection = _get_collection()
    industries = _ensure_industries_indexed(collection)
    results = collection.query(query_texts=[description], n_results=min(top_k, len(industries)))
    if not results or not results["ids"] or not results["ids"][0]:
        return []
    indices = [int(idx) for idx in results["ids"][0]]
    entries: list[MarketEntry] = []
    for idx in indices:
        ind = industries[idx]
        growth = growth_rate_from_sizes(ind.sizes)
        entries.append(
            MarketEntry(
                name=ind.name,
                sector=ind.sector,
                growth_rate=growth,
                sizes_2023_2026_in_millions=ind.sizes,
            )
        )
    return entries
