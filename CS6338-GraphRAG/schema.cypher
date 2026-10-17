// Neo4j 5.26; use a dedicated project database. No sample/gold edges are inserted.
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:SourceDocument) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (n:Chunk) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT assertion_id IF NOT EXISTS FOR (n:Assertion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT stix_relation_id IF NOT EXISTS FOR (n:STIXRelation) REQUIRE n.id IS UNIQUE;
CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name);
CREATE INDEX assertion_tuple IF NOT EXISTS FOR (n:Assertion) ON (n.source_id,n.predicate,n.target_id);
CREATE VECTOR INDEX chunk_text IF NOT EXISTS FOR (n:Chunk) ON (n.text_embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};
CREATE VECTOR INDEX entity_graph IF NOT EXISTS FOR (n:Entity) ON (n.graph_embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 128, `vector.similarity_function`: 'cosine'}};
