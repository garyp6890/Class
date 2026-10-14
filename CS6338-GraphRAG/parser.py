"""Validate extraction syntax, IDs, types and verbatim evidence; no gold access."""
import json
from pathlib import Path
from schemas import Extraction

ALLOWED = {
    'USES': {('ThreatGroup','Software'),('ThreatGroup','Technique'),('Software','Technique')},
    'MITIGATED_BY': {('Technique','Mitigation')},
    'ASSOCIATED_WITH': {('ThreatGroup','Campaign'),('ThreatGroup','Software')}
}

def parse_extraction(raw: str, chunk_text: str, catalog: dict):
    result=Extraction.model_validate_json(raw)
    entities={e.id:e for e in result.entities}
    if len(entities)!=len(result.entities):raise ValueError('Duplicate entity ID')
    for entity in result.entities:
        known=catalog.get(entity.id)
        if known is None or known['entity_type']!=entity.entity_type.value:
            raise ValueError('Unknown or mistyped canonical ID')
        if entity.name.casefold() not in {known['name'].casefold(),*(x.casefold() for x in known['aliases'])}:
            raise ValueError('Name does not match canonical catalog')
    buckets={'accepted':[],'review':[],'rejected':[]}
    for edge in result.relations:
        if edge.source_id not in entities or edge.target_id not in entities:
            raise ValueError('Dangling endpoint')
        pair=(entities[edge.source_id].entity_type.value,entities[edge.target_id].entity_type.value)
        if pair not in ALLOWED[edge.predicate]:raise ValueError('Invalid predicate direction/type')
        if edge.evidence_text not in chunk_text:raise ValueError('Evidence is not verbatim')
        bucket='accepted' if edge.confidence>=0.85 else 'review' if edge.confidence>=0.60 else 'rejected'
        buckets[bucket].append(edge.model_dump(mode='json'))
    return {'entities':[e.model_dump(mode='json') for e in result.entities],**buckets}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('response');p.add_argument('chunk_text')
    a=p.parse_args();root=Path(__file__).parent
    catalog={x['id']:x for x in json.loads((root/'data/entities.json').read_text(encoding='utf-8'))}
    print(json.dumps(parse_extraction(Path(a.response).read_text(encoding='utf-8'),
        Path(a.chunk_text).read_text(encoding='utf-8'),catalog),indent=2))
