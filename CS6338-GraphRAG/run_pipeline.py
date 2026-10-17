"""Reproducible final execution stages; failures are artifacts, never invented metrics."""
import argparse, hashlib, json, os, platform, time, urllib.request
from pathlib import Path
from chunking import chunk_document
from extract import extract
from evaluate_triples import score
from init_db import driver
from ingest import ingest
from embeddings import text_embedding

ROOT=Path(__file__).parent
OUT=ROOT/'results'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str),encoding='utf-8');tmp.replace(p)
def chunks():return [c for d in read(ROOT/'data/documents.json') for c in chunk_document(d)]

def extraction():
    catalog={e['id']:e for e in read(ROOT/'data/entities.json')}
    rows=read(OUT/'extraction.json') if (OUT/'extraction.json').exists() else []
    done={r['chunk_id'] for r in rows}
    for c in chunks():
        if c.chunk_id in done:continue
        start=time.perf_counter();result=extract(c,catalog)
        rows.append({'chunk_id':c.chunk_id,'document_id':c.document_id,'elapsed_ms':1000*(time.perf_counter()-start),**result})
        save(OUT/'extraction.json',rows)
        print(f"extracted {len(rows)}/{len(chunks())}: {len(result.get('accepted',[]))} accepted",flush=True)
    predictions=[{'document_id':r['document_id'],**e} for r in rows for e in r.get('accepted',[])]
    save(OUT/'predictions.json',predictions)
    gold=read(ROOT/'data/gold_triples.json')
    metrics={}
    for split in ('development','test'):
        g=[r for r in gold if r['split']==split];docs={r['document_id'] for r in g}
        p=[r for r in predictions if r['document_id'] in docs]
        metrics[split]={'micro':score(g,p),'by_predicate':{k:score([r for r in g if r['predicate']==k],[r for r in p if r['predicate']==k]) for k in sorted({r['predicate'] for r in g+p})}}
    metrics['quarantined']=sum(r.get('status')=='quarantined' for r in rows)
    metrics['note']='STIX silver reference; includes gold-038 association/USES discrepancy; no manual relabeling'
    save(OUT/'extraction_metrics.json',metrics)

def load():
    catalog={e['id']:e for e in read(ROOT/'data/entities.json')};byid={c.chunk_id:c for c in chunks()}
    rows=read(OUT/'extraction.json')
    with driver() as db,db.session(database=os.getenv('NEO4J_DATABASE','neo4j')) as s:
        schema=(ROOT/'schema.cypher').read_text(encoding='utf-8')
        schema='\n'.join(x for x in schema.splitlines() if not x.lstrip().startswith('//'))
        for statement in schema.split(';'):
            if statement.strip():s.run(statement).consume()
        from structured_ingest import ingest_structured
        structured=s.execute_write(ingest_structured)
        (OUT/'ontology.ttl').write_text(structured.pop('rdf_turtle'),encoding='utf-8')
        save(OUT/'structured_ingestion.json',structured)
        for r in rows:
            c=byid[r['chunk_id']]
            raw=r.get('raw',json.dumps({'entities':[],'relations':[]}))
            s.execute_write(ingest,c,raw,catalog)
        def counts():return dict(s.run('''MATCH (n) RETURN count(n) AS nodes,
            count(CASE WHEN n:Assertion THEN 1 END) AS assertions,
            count(CASE WHEN n:Chunk THEN 1 END) AS chunks''').single())
        before=counts()
        for r in rows:s.execute_write(ingest,byid[r['chunk_id']],r.get('raw',json.dumps({'entities':[],'relations':[]})),catalog)
        after=counts()
        if before!=after:raise RuntimeError('Idempotency failed')
        # Deliberately abort a write and verify that rollback removed it.
        try:
            with s.begin_transaction(timeout=5) as tx:
                tx.run("CREATE (:RollbackProbe {id:'capstone-rollback'})").consume()
                raise RuntimeError('intentional rollback')
        except RuntimeError:pass
        rolled=s.run("MATCH (n:RollbackProbe {id:'capstone-rollback'}) RETURN count(n) AS n").single()['n']==0
        for c in byid.values():
            v=text_embedding(c.text)
            s.run('MATCH (c:Chunk {id:$id}) SET c.text_embedding=$v',id=c.chunk_id,v=v).consume()
        s.run('CALL db.awaitIndexes(120)').consume()
        stats={'first_load':before,'second_load':after,'idempotent':before==after,'rollback_verified':rolled,
            'relationships':[dict(r) for r in s.run('MATCH ()-[r]->() RETURN type(r) AS type,count(*) AS count ORDER BY type')],
            'indexes':[dict(r) for r in s.run('SHOW INDEXES YIELD name,state RETURN name,state')],
            'neo4j':[dict(r) for r in s.run('CALL dbms.components() YIELD name,versions RETURN name,versions')]}
        save(OUT/'ingestion.json',stats)

def analytics(seed):
    from neo4j import Query
    with driver() as db,db.session(database=os.getenv('NEO4J_DATABASE','neo4j')) as s:
        name='cti_final'
        if s.run('CALL gds.graph.exists($n) YIELD exists RETURN exists',n=name).single()['exists']:
            s.run('CALL gds.graph.drop($n)',n=name).consume()
        projection=dict(s.run('''CALL gds.graph.project($name,'Entity',{
          USES:{orientation:'UNDIRECTED'},MITIGATED_BY:{orientation:'UNDIRECTED'},
          ASSOCIATED_WITH:{orientation:'UNDIRECTED'}})
          YIELD nodeCount,relationshipCount RETURN nodeCount,relationshipCount''',name=name).single())
        rank=[dict(r) for r in s.run('''CALL gds.pageRank.stream($name,{dampingFactor:0.85,maxIterations:20})
            YIELD nodeId,score RETURN gds.util.asNode(nodeId).id AS id,score ORDER BY score DESC,id''',name=name)]
        wcc=[dict(r) for r in s.run('CALL gds.wcc.stats($name) YIELD componentCount,componentDistribution RETURN componentCount,componentDistribution',name=name)]
        start=time.perf_counter()
        fit=dict(s.run(Query('''CALL gds.node2vec.write($name,{embeddingDimension:128,walkLength:30,
            walksPerNode:80,returnFactor:1.0,inOutFactor:0.5,windowSize:5,negativeSamplingRate:5,
            iterations:20,concurrency:1,randomSeed:$seed,writeProperty:'graph_embedding'})
            YIELD nodePropertiesWritten,computeMillis RETURN nodePropertiesWritten,computeMillis''',timeout=300),name=name,seed=seed).single())
        vectors=[dict(r) for r in s.run('MATCH (n:Entity) WHERE n.graph_embedding IS NOT NULL RETURN n.id AS id,n.graph_embedding AS vector ORDER BY id')]
        if any(len(r['vector'])!=128 for r in vectors):raise RuntimeError('Wrong embedding dimension')
        save(OUT/f'graph_vectors_{seed}.json',vectors)
        save(OUT/f'analytics_{seed}.json',{'seed':seed,'gds':s.run('RETURN gds.version() AS v').single()['v'],
             'projection':projection,'pagerank':rank,'wcc':wcc,'node2vec':fit,'elapsed_ms':1000*(time.perf_counter()-start)})

def benchmark(seed):
    from engine import LiveQAEngine
    from schemas import GraphRAGQueryRequest
    engine=LiveQAEngine(seed);path=OUT/f'benchmark_{seed}.json'
    rows=read(path) if path.exists() else [];done={(r['id'],r['mode']) for r in rows}
    questions=[q for q in read(ROOT/'data/eval_queries.json') if q['split']=='test']
    for mode in ('text_only','hybrid_without_node2vec','hybrid'):
        for q in questions:
            if (q['id'],mode) in done:continue
            start=time.perf_counter();row={'id':q['id'],'seed':seed,'mode':mode,'user_input':q['question'],'reference':q['reference_answer']}
            try:
                response=engine.query(GraphRAGQueryRequest(query=q['question'],mode=mode))
                trace=engine.last_trace
                docs={c['document_id'] for c in trace['contexts']}
                row.update(response.model_dump(mode='json'),response=response.answer,
                    retrieved_contexts=[c['text'] for c in trace['contexts']],trace=trace,
                    evidence_recall=len(docs&set(q['supporting_document_ids']))/len(q['supporting_document_ids']),
                    path_ids_mentioned=all(e in response.answer for e in q['expected_path']))
            except Exception as error:
                row.update(error=type(error).__name__+': '+str(error),execution_time_ms=1000*(time.perf_counter()-start),trace=engine.last_trace)
            rows.append(row);save(path,rows);print(f"{seed} {mode} {q['id']}: {row.get('status',row.get('error'))}",flush=True)

def manifest():
    import importlib.metadata as md
    data={'python':platform.python_version(),'platform':platform.platform(),
        'packages':{n:md.version(n) for n in ('pydantic','neo4j','fastapi','networkx','gensim')},
        'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('data','prompts') for p in (ROOT/folder).rglob('*') if p.is_file()},
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}}
    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=10) as r:data['models']=json.load(r)
    with urllib.request.urlopen('http://127.0.0.1:11434/api/version',timeout=10) as r:data['ollama']=json.load(r)
    data['evaluation_protocol']={'seeds':[42,43,44],'temperature':0,'ragas':'0.2.15',
        'judge':'qwen2.5:14b','relevancy_strictness':1,'judge_context':8192,'judge_output_limit':2048,
        'judge_cohort_seed':42,
        'context_budget_bytes':6000,'graph_hops':2,'default_top_k_chunks':5}
    save(OUT/'manifest.json',data)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['extract','load','analytics','benchmark','manifest']);p.add_argument('--seed',type=int,default=42);a=p.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.stage in ('analytics','benchmark'):globals()[a.stage](a.seed)
    else:{'extract':extraction,'load':load,'manifest':manifest}[a.stage]()
