from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class EntityType(str, Enum):
    GROUP='ThreatGroup'
    SOFTWARE='Software'
    TECHNIQUE='Technique'
    MITIGATION='Mitigation'
    CAMPAIGN='Campaign'

class Entity(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    entity_type: EntityType
    aliases: list[str] = Field(default_factory=list)

class Relation(StrictModel):
    source_id: str
    target_id: str
    predicate: Literal['USES','MITIGATED_BY','ASSOCIATED_WITH']
    evidence_text: str = Field(min_length=1)
    confidence: float = Field(ge=0,le=1)

class Extraction(StrictModel):
    entities: list[Entity]
    relations: list[Relation]

class GraphChunk(StrictModel):
    chunk_id: str
    document_id: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    source_url: str
    entity_ids: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def valid_span(self):
        if self.end-self.start != len(self.text):
            raise ValueError('Chunk offsets must match its text length')
        return self

class GraphRAGQueryRequest(StrictModel):
    query: str = Field(min_length=3,max_length=2000)
    mode: Literal['text_only','hybrid'] = 'hybrid'
    top_k_chunks: int = Field(default=5,ge=1,le=10)
    max_hop_distance: int = Field(default=2,ge=1,le=2)
    enable_reasoning_rules: bool = True

class Citation(StrictModel):
    chunk_id: str
    document_id: str
    source_url: str
    evidence_text: str

class SubgraphContext(StrictModel):
    nodes: list[Entity] = Field(default_factory=list)
    edges: list[Relation] = Field(default_factory=list)
    cypher_template_id: str | None = None

class GraphRAGResponse(StrictModel):
    answer: str
    status: Literal['answered','insufficient_evidence']
    citations: list[Citation]
    retrieved_subgraph: SubgraphContext
    execution_time_ms: float = Field(ge=0)
    generated_at: datetime = Field(default_factory=lambda:datetime.now(timezone.utc))
