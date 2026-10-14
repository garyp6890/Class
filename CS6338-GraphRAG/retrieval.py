"""Bounded query templates and fusion primitive for the planned QA engine."""
TEXT_SEARCH='''CALL db.index.vector.queryNodes('chunk_text',$k,$vector)
YIELD node,score RETURN node.id AS chunk_id,node.text AS text,score'''
# Hop counts are selected from constants, never supplied as arbitrary Cypher.
PATHS={h:f'''MATCH p=(s:Entity)-[:USES|MITIGATED_BY|ASSOCIATED_WITH*1..{h}]->(t:Entity)
WHERE s.id IN $anchor_ids
RETURN p ORDER BY length(p),t.id LIMIT $path_limit''' for h in (1,2)}
GRAPH_NEIGHBORS='''MATCH (n:Entity {id:$anchor_id})
WHERE n.graph_embedding IS NOT NULL
CALL db.index.vector.queryNodes('entity_graph',$k,n.graph_embedding)
YIELD node,score RETURN node.id AS entity_id,score'''

def rrf(text_ids,graph_ids,k=60,limit=5):
    scores={}
    for ids in (text_ids,graph_ids):
        for rank,cid in enumerate(dict.fromkeys(ids),1):scores[cid]=scores.get(cid,0)+1/(k+rank)
    return sorted(scores,key=lambda cid:(-scores[cid],cid))[:limit]
