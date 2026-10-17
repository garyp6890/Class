"""Import frozen STIX metadata separately from text-predicted assertions.

STIXRelation records preserve the ontology mapping without supplying reference
edges to the QA graph or its analytics projection. This prevents evaluation leakage.
"""
import json
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, RDFS

ROOT=Path(__file__).parent
CTI=Namespace('https://example.org/cs6338/cti/')
def ingest_structured(tx):
    entities=json.loads((ROOT/'data/entities.json').read_text(encoding='utf-8'))
    stix=json.loads((ROOT/'data/source/attack_subset_19.2.json').read_text(encoding='utf-8'))
    graph=Graph();graph.bind('cti',CTI)
    catalog={e['id']:e for e in entities};ids={}
    for obj in stix['objects']:
        refs=[r.get('external_id') for r in obj.get('external_references',[]) if r.get('source_name')=='mitre-attack']
        if refs and refs[0] in catalog:
            eid=refs[0];ids[obj['id']]=eid;e=catalog[eid]
            tx.run('''MERGE (n:Entity {id:$id}) SET n.name=$name,n.aliases=$aliases,
                n.stix_id=$stix,n.ontology_class=$kind''',id=eid,name=e['name'],aliases=e['aliases'],stix=obj['id'],kind=obj['type']).consume()
            graph.add((CTI[eid],RDF.type,CTI[e['entity_type']]))
            graph.add((CTI[eid],RDFS.label,Literal(e['name'])))
    total=0
    for obj in stix['objects']:
        if obj['type']!='relationship':continue
        if obj['source_ref'] not in ids or obj['target_ref'] not in ids:continue
        total+=1
        tx.run('''MERGE (s:STIXRelation {id:$id}) SET s.source_id=$source,s.target_id=$target,
            s.stix_type=$type,s.modified=$modified,s.provenance='MITRE ATT&CK 19.2 STIX' ''',
            id=obj['id'],source=ids[obj['source_ref']],target=ids[obj['target_ref']],type=obj['relationship_type'],modified=obj.get('modified')).consume()
    return {'structured_entities':len(ids),'structured_relationship_records':total,
            'rdf_triples':len(graph),'rdf_turtle':graph.serialize(format='turtle')}
