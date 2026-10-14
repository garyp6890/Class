"""Persist validated accepted extractions, not reference STIX edges."""
import hashlib
from schemas import EntityType
from parser import parse_extraction
import json

def ingest(tx,chunk,raw,catalog):
    parsed=parse_extraction(raw,chunk.text,catalog)
    tx.run('''MERGE (d:SourceDocument {id:$document_id}) SET d.source_url=$source_url
        MERGE (c:Chunk {id:$chunk_id}) SET c.text=$text,c.start=$start,c.end=$end
        MERGE (d)-[:HAS_CHUNK]->(c)''',**chunk.model_dump(exclude={'entity_ids'})).consume()
    for e in parsed['entities']:
        label=e['entity_type']
        assert label in {x.value for x in EntityType}
        canonical=catalog[e['id']]
        tx.run(f'''MERGE (n:Entity {{id:$id}}) SET n:{label},n.name=$name,n.aliases=$aliases
            WITH n MATCH (c:Chunk {{id:$chunk_id}}),(d:SourceDocument {{id:$document_id}})
            MERGE (c)-[:MENTIONS_ENTITY]->(n) MERGE (n)-[:MENTIONED_IN]->(d)''',
            id=e['id'],name=canonical['name'],aliases=canonical['aliases'],
            chunk_id=chunk.chunk_id,document_id=chunk.document_id).consume()
    for r in parsed['accepted']:
        key=json.dumps([chunk.document_id,r['source_id'],r['predicate'],r['target_id']],ensure_ascii=False)
        aid=hashlib.sha256(key.encode()).hexdigest()
        # Predicate is schema-validated before interpolation; values remain parameters.
        tx.run(f'''MATCH (s:Entity {{id:$source_id}}),(o:Entity {{id:$target_id}}),
            (c:Chunk {{id:$chunk_id}})
            MERGE (a:Assertion {{id:$aid}})
            SET a.source_id=$source_id,a.target_id=$target_id,a.predicate=$predicate,
                a.confidence=$confidence
            MERGE (a)-[:SUBJECT]->(s) MERGE (a)-[:OBJECT]->(o)
            MERGE (a)-[ev:SUPPORTED_BY]->(c) SET ev.evidence_text=$evidence_text
            MERGE (s)-[r:{r['predicate']} {{assertion_id:$aid}}]->(o)
            SET r.document_id=$document_id,r.confidence=$confidence,r.derived=false''',
            **r,aid=aid,chunk_id=chunk.chunk_id,document_id=chunk.document_id).consume()
    return parsed
