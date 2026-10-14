"""Check reference integrity, not human annotation quality or model accuracy."""
import json
from pathlib import Path

def validate():
    root=Path(__file__).parent/'data'
    read=lambda n:json.loads((root/n).read_text(encoding='utf-8'))
    docs={x['document_id']:x for x in read('documents.json')}
    entities={x['id']:x for x in read('entities.json')}
    gold=read('gold_triples.json');queries=read('eval_queries.json')
    source={x['id']:x for x in read('source/attack_subset_19.2.json')['objects']}
    aid=lambda o:next(x['external_id'] for x in o['external_references'] if x.get('source_name')=='mitre-attack' and 'external_id' in x)
    assert len(gold)>=50 and sum(q['split']=='test' for q in queries)>=20
    assert len({g['id'] for g in gold})==len(gold)
    for g in gold:
        assert g['subject_id'] in entities and g['object_id'] in entities
        assert g['evidence_text'] in docs[g['document_id']]['text']
        r=source[g['source_relationship_id']]
        s,t=aid(source[r['source_ref']]),aid(source[r['target_ref']])
        expected=(t,'MITIGATED_BY',s) if r['relationship_type']=='mitigates' else (s,'USES',t)
        assert (g['subject_id'],g['predicate'],g['object_id'])==expected
        assert not r.get('revoked') and not r.get('x_mitre_deprecated')
    byid={g['id']:g for g in gold}
    for q in queries:
        edges=[byid[i] for i in q['supporting_triple_ids']]
        assert len(edges)==q['hops']==2
        assert [edges[0]['subject_id'],edges[0]['object_id'],edges[1]['object_id']]==q['expected_path']
        assert edges[0]['object_id']==edges[1]['subject_id']
        assert [e['document_id'] for e in edges]==q['supporting_document_ids']
    return dict(documents=len(docs),entities=len(entities),reference_triples=len(gold),qa_pairs=len(queries),
        test_qa=sum(q['split']=='test' for q in queries),student_review='pending')

if __name__=='__main__':print(json.dumps(validate(),indent=2))
