from pydantic import BaseModel


class CompetitorEntry(BaseModel):
    name: str
    description: str
    revenue: str
    features: str
    strengths: str
    weaknesses: str
    online_presence: str


class CompetitorAnalysis(BaseModel):
    competitors: list[CompetitorEntry]
    overview: str
    sources: list[str]
    score: int


class CompetitorDiscoveryResponse(BaseModel):
    competitors: list[CompetitorEntry]


class CompetitorScoreResponse(BaseModel):
    score: int
