// Query-time inverse rule. Do not create duplicate evidence or transitive USES.
// Uses(x,y) => UsedBy(y,x), retaining the same supporting assertion/chunk.
MATCH (a:Assertion {predicate:'USES'})-[:SUBJECT]->(x:Entity)
MATCH (a)-[:OBJECT]->(y:Entity)
MATCH (a)-[:SUPPORTED_BY]->(c:Chunk)
WHERE y.id = $entity_id
RETURN y.id AS subject_id, 'USED_BY' AS predicate, x.id AS object_id,
       a.id AS assertion_id, c.id AS chunk_id, true AS derived;
