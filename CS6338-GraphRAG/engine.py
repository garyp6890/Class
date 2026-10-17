"""Live retrieval and generation. No gold labels or reference answers are read here."""
import json, os, re, time, urllib.request
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from typing import Literal
from schemas import GraphRAGResponse, Citation, SubgraphContext
from embeddings import text_embedding
from init_db import driver
from retrieval import TEXT_SEARCH, GRAPH_NEIGHBORS, rrf
from resolve import resolve

ROOT=Path(__file__).parent
class GeneratedAnswer(BaseModel):
    model_config=ConfigDict(extra='forbid')
    answer:str
    status:Literal['answered','insufficient_evidence']
    cited_chunk_ids:list[str]

class LiveQAEngine:
    def __init__(self,seed=42):
        self.seed=seed
        self.last_trace={}

    def health(self):
        try:
            with driver() as db,db.session(database=os.getenv('NEO4J_DATABASE','neo4j')) as s:
                populated=s.run('MATCH (c:Chunk) WHERE c.text_embedding IS NOT NULL RETURN count(c) AS n').single()['n']>0
            with urllib.request.urlopen(os.getenv('OLLAMA_HOST','http://127.0.0.1:11434')+'/api/tags',timeout=5) as r:
                models=[m['name'] for m in json.load(r)['models']]
            ready=populated and all(m in models for m in ('llama3.1:8b','nomic-embed-text:v1.5'))
            return {'status':'ready' if ready else 'dependencies_not_ready','engine_ready':ready}
        except Exception:
            return {'status':'dependencies_unavailable','engine_ready':False}

    def query(self,request):
        self.last_trace={}
        started=time.perf_counter()
        vector=text_embedding(request.query,is_query=True,base_url=os.getenv('OLLAMA_HOST','http://127.0.0.1:11434'))
        with driver() as db,db.session(database=os.getenv('NEO4J_DATABASE','neo4j')) as session:
            catalog=[dict(r) for r in session.run('MATCH (n:Entity) RETURN n.id AS id,n.name AS name,n.aliases AS aliases')]
            anchors=[]
            q=request.query.casefold()
            explicit=[e['id'] for e in catalog if re.search(r'(?<!\w)'+re.escape(e['id'].casefold())+r'(?!\w)',q)]
            for e in catalog:
                names=[n for n in [e['id'],e['name'],*(e['aliases'] or [])] if re.search(r'(?<!\w)'+re.escape(n.casefold())+r'(?!\w)',q)]
                # Ambiguous names remain unresolved unless an explicit ID in the query resolves them.
                typed=[{**r,'entity_type':'Entity'} for r in catalog]
                if any(resolve(n,'Entity',typed,explicit).get('id')==e['id'] for n in names):
                    anchors.append(e['id'])
            text=[dict(r) for r in session.run(TEXT_SEARCH,k=20,vector=vector)]
            graph_ids=[];facts=[]
            if request.mode!='text_only' and anchors:
                candidates=list(anchors)
                if request.mode=='hybrid':
                    for aid in anchors:
                        candidates.extend(r['entity_id'] for r in session.run(GRAPH_NEIGHBORS,anchor_id=aid,k=5))
                # Only persisted directed edges and their supporting chunks can supply evidence.
                hops=request.max_hop_distance
                direction='-' if request.enable_reasoning_rules else '->'
                path_pattern=f'(s:Entity)-[:USES|MITIGATED_BY|ASSOCIATED_WITH*1..{hops}]{direction}(t:Entity)'
                cypher=f'''MATCH p={path_pattern} WHERE s.id IN $ids
                    UNWIND relationships(p) AS r
                    WITH DISTINCT r MATCH (a:Assertion {{id:r.assertion_id}})-[ev:SUPPORTED_BY]->(c:Chunk)
                    RETURN a.source_id AS source_id,a.target_id AS target_id,a.predicate AS predicate,
                    a.confidence AS confidence,c.id AS chunk_id,ev.evidence_text AS evidence_text
                    ORDER BY source_id,predicate,target_id,chunk_id LIMIT 120'''
                facts=[dict(r) for r in session.run(cypher,ids=candidates)]
                # Rank paths connected to explicit anchors ahead of structural proposals.
                facts.sort(key=lambda f:(not (f['source_id'] in anchors or f['target_id'] in anchors),f['chunk_id']))
                graph_ids=list(dict.fromkeys(f['chunk_id'] for f in facts))
            selected=[r['chunk_id'] for r in text[:request.top_k_chunks]] if request.mode=='text_only' else rrf(
                [r['chunk_id'] for r in text],graph_ids,limit=request.top_k_chunks)
            contexts=[dict(r) for r in session.run('''UNWIND $ids AS id MATCH (d:SourceDocument)-[:HAS_CHUNK]->(c:Chunk {id:id})
                RETURN c.id AS chunk_id,c.text AS text,d.id AS document_id,d.source_url AS source_url''',ids=selected)]
        contexts.sort(key=lambda c:selected.index(c['chunk_id']))
        # A conservative byte cap also bounds byte-level tokenizer pieces to <=6000.
        packed=[];used=0
        for c in contexts:
            cost=len(json.dumps(c,ensure_ascii=False).encode('utf-8'))
            if used+cost<=5500:packed.append(c);used+=cost
        allowed={c['chunk_id']:c for c in packed}
        facts=[f for f in facts if f['chunk_id'] in allowed]
        while len(json.dumps({'text':packed,'graph':facts}).encode('utf-8'))>6000 and packed:
            packed.pop();allowed={c['chunk_id']:c for c in packed};facts=[f for f in facts if f['chunk_id'] in allowed]
        retrieved_ms=(time.perf_counter()-started)*1000
        labels={f'C{i+1}':c for i,c in enumerate(packed)}
        reverse={c['chunk_id']:label for label,c in labels.items()}
        model_context=[{**c,'chunk_id':label} for label,c in labels.items()]
        model_facts=[{**f,'chunk_id':reverse[f['chunk_id']]} for f in facts]
        prompt=(ROOT/'prompts/answer.txt').read_text(encoding='utf-8').split('USER TEMPLATE')[0]
        payload={'model':'llama3.1:8b','stream':False,'format':GeneratedAnswer.model_json_schema(),
                 'messages':[{'role':'system','content':prompt},{'role':'user','content':json.dumps({
                     'question':request.query,'TEXT':model_context,'GRAPH':model_facts})}],
                 'options':{'temperature':0,'seed':self.seed,'num_ctx':8192,'num_predict':700}}
        req=urllib.request.Request(os.getenv('OLLAMA_HOST','http://127.0.0.1:11434')+'/api/chat',
             data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=180) as r:raw=json.load(r)
        self.last_trace={'retrieval_ms':retrieved_ms,'contexts':packed,'facts':facts,'anchors':anchors,
                         'raw':raw,'seed':self.seed,'citation_map':{label:c['chunk_id'] for label,c in labels.items()}}
        if raw.get('done_reason')=='length':raise ValueError('Truncated answer')
        answer=GeneratedAnswer.model_validate_json(raw['message']['content'])
        ids=list(dict.fromkeys(answer.cited_chunk_ids))
        inline=re.findall(r'\[([^\[\]]+)\]',answer.answer)
        invalid=[i for i in ids+inline if i not in labels]
        if invalid or (answer.status=='answered' and not ids):
            raise ValueError('Answer contains absent or invalid citations')
        citations=[Citation(citation_id=i,chunk_id=labels[i]['chunk_id'],document_id=labels[i]['document_id'],source_url=labels[i]['source_url'],
                   evidence_text=labels[i]['text']) for i in ids]
        self.last_trace['citation_ids_valid']=True
        return GraphRAGResponse(answer=answer.answer,status=answer.status,citations=citations,
            retrieved_subgraph=SubgraphContext(edges=[{k:f[k] for k in ('source_id','target_id','predicate','confidence','evidence_text')} for f in facts],
                cypher_template_id=None if request.mode=='text_only' else 'bounded_paths'),
            execution_time_ms=(time.perf_counter()-started)*1000)
