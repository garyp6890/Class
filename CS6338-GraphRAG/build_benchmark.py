"""Build a bounded reference benchmark from official ATT&CK 19.2 records."""
import json,re,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).parent
SOURCE='https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack-19.2.json'
source_path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/source/enterprise-attack-19.2.json'
if source_path.exists():
    raw=json.loads(source_path.read_text(encoding='utf-8'))
else:
    with urllib.request.urlopen(SOURCE,timeout=120) as response:raw=json.load(response)
objects={o['id']:o for o in raw['objects'] if not o.get('revoked') and not o.get('x_mitre_deprecated')}
def aid(o):
    return next((x['external_id'] for x in o.get('external_references',[]) if x.get('source_name')=='mitre-attack' and 'external_id' in x),None)
def url(o):
    return next((x['url'] for x in o.get('external_references',[]) if x.get('source_name')=='mitre-attack' and 'url' in x),SOURCE)
def rel_ok(r):
    return (r['type']=='relationship' and r.get('source_ref') in objects and r.get('target_ref') in objects
        and 35<len(r.get('description',''))<1700
        and len(re.sub(r'\(Citation:[^)]*\)','',r.get('description','')).strip())>40
        and aid(objects[r['source_ref']]) and aid(objects[r['target_ref']]))
rels=sorted([o for o in objects.values() if rel_ok(o)],key=lambda r:(aid(objects[r['source_ref']]),aid(objects[r['target_ref']]),r['id']))
mitigations={}
for r in rels:
    if r['relationship_type']=='mitigates':mitigations.setdefault(r['target_ref'],[]).append(r)
selected={}
paths=[]
for name in ['APT29','APT28','FIN7','Lazarus Group']:
    group=next(o for o in objects.values() if o.get('name')==name)
    candidates=[r for r in rels if r['source_ref']==group['id'] and r['relationship_type']=='uses'
                and objects[r['target_ref']]['type']=='attack-pattern' and r['target_ref'] in mitigations]
    for r in candidates[:5]:
        m=mitigations[r['target_ref']][0]
        selected[r['id']]=r;selected[m['id']]=m
        paths.append((r,m))
# Include software paths so the checkpoint covers the proposal's core schema.
software_paths=[]
for name in ['APT29','APT28','FIN7','Lazarus Group']:
    group=next(o for o in objects.values() if o.get('name')==name)
    gs=[r for r in rels if r['source_ref']==group['id'] and r['relationship_type']=='uses'
        and objects[r['target_ref']]['type'] in ('malware','tool')]
    for g in gs:
        st=next((r for r in rels if r['source_ref']==g['target_ref'] and r['relationship_type']=='uses'
                 and objects[r['target_ref']]['type']=='attack-pattern'),None)
        if st:
            selected[g['id']]=g;selected[st['id']]=st;software_paths.append((g,st));break
for r in rels:
    if len(selected)>=60:break
    if (r['relationship_type']=='uses' and objects[r['source_ref']].get('name') in ['APT29','APT28','FIN7','Lazarus Group']
            and objects[r['target_ref']]['type'] in ('malware','tool','attack-pattern')):selected[r['id']]=r
assert len(selected)==60 and len(paths)==20 and len(software_paths)>=1
types={'intrusion-set':'ThreatGroup','malware':'Software','tool':'Software','attack-pattern':'Technique','course-of-action':'Mitigation','campaign':'Campaign'}
entities={};docs=[];gold=[];idmap={}
for i,r in enumerate(selected.values(),1):
    a,b=objects[r['source_ref']],objects[r['target_ref']]
    for o in [a,b]:
        entities[aid(o)]={'id':aid(o),'name':o['name'],'entity_type':types[o['type']],
            'aliases':o.get('aliases',o.get('x_mitre_aliases',[])),'source_url':url(o),
            'software_type':o['type'] if types[o['type']]=='Software' else None}
    doc_id=f'attack19.2:{r["id"]}'
    # Identity context comes from STIX endpoints; no relationship_type field is provided to the extractor.
    text=f'Record context: {a["name"]} ({aid(a)}); {b["name"]} ({aid(b)}).\n\n{r["description"]}'
    docs.append({'document_id':doc_id,'text':text,'source_url':url(b),'record_id':r['id'],
        'release':'19.2','references':r.get('external_references',[]),'kind':'ATT&CK relationship narrative'})
    subject,object_,predicate=(aid(b),aid(a),'MITIGATED_BY') if r['relationship_type']=='mitigates' else (aid(a),aid(b),'USES')
    gid=f'gold-{i:03d}';idmap[r['id']]=gid
    gold.append({'id':gid,'subject_id':subject,'predicate':predicate,'object_id':object_,
        'document_id':doc_id,'evidence_text':r['description'],'source_relationship_id':r['id'],
        'split':'development' if i%5==0 else 'test','annotation_basis':'official STIX relation with narrative evidence',
        'student_review_status':'pending'})
queries=[]
for i,(r,m) in enumerate(paths,1):
    a,t,mit=objects[r['source_ref']],objects[r['target_ref']],objects[m['source_ref']]
    queries.append({'id':f'qa-{i:02d}','split':'test',
        'question':f'In this frozen subset, which mitigation is linked to {t["name"]} ({aid(t)}) as reported for {a["name"]}, and what is the two-edge evidence path?',
        'reference_answer':f'{a["name"]} ({aid(a)}) USES {t["name"]} ({aid(t)}), which is MITIGATED_BY {mit["name"]} ({aid(mit)}). This is a recorded association, not proof that the mitigation prevents every occurrence.',
        'expected_path':[aid(a),aid(t),aid(mit)],'supporting_triple_ids':[idmap[r['id']],idmap[m['id']]],
        'supporting_document_ids':[f'attack19.2:{x["id"]}' for x in [r,m]],'hops':2})
for i,(g,s) in enumerate(software_paths,21):
    a,soft,t=objects[g['source_ref']],objects[g['target_ref']],objects[s['target_ref']]
    queries.append({'id':f'qa-{i:02d}','split':'development',
        'question':f'Which technique in the frozen subset connects {a["name"]} through {soft["name"]}, and what evidence supports both links?',
        'reference_answer':f'{a["name"]} ({aid(a)}) USES {soft["name"]} ({aid(soft)}), and {soft["name"]} USES {t["name"]} ({aid(t)}).',
        'expected_path':[aid(a),aid(soft),aid(t)],'supporting_triple_ids':[idmap[g['id']],idmap[s['id']]],
        'supporting_document_ids':[f'attack19.2:{x["id"]}' for x in [g,s]],'hops':2})
def write(name,value):
    p=ROOT/'data'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
write('documents.json',docs);write('entities.json',list(entities.values()));write('gold_triples.json',gold);write('eval_queries.json',queries)
subset_ids=set(selected)|{x[k] for x in selected.values() for k in ['source_ref','target_ref']}
write('source/attack_subset_19.2.json',{'type':'bundle','id':raw['id'],'objects':[objects[i] for i in sorted(subset_ids)]})
write('dataset_info.json',{'release':'19.2','source_url':SOURCE,'retrieved':'2026-10-14','documents':len(docs),
    'entities':len(entities),'gold_triples':len(gold),'qa_pairs':len(queries),
    'scope':'4 groups plus selected software, techniques and mitigations; no campaigns in this first subset',
    'annotation_note':'Reference labels are derived from official STIX, not LLM predictions. Human review is still required before calling this a manually reviewed gold set.',
    'evaluation_note':'Extraction is scored per record for its designated endpoint pair, not every incidental claim mentioned in the description. QA answers are scoped to the selected reference paths.',
    'source_overlap_note':'Development and test QA have distinct questions but can share entities and narrative records; this is an in-corpus benchmark.'})
print(json.dumps({'entities':len(entities),'types':{t:sum(e['entity_type']==t for e in entities.values()) for t in types.values()},'triples':len(gold),'qa':len(queries)},indent=2))
for row in gold:print(row['id'],row['subject_id'],row['predicate'],row['object_id'],row['evidence_text'][:240])
