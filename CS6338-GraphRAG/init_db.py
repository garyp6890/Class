"""Apply idempotent schema to the database named in NEO4J_DATABASE."""
import os
from pathlib import Path
from neo4j import GraphDatabase

def driver():
    return GraphDatabase.driver(os.getenv('NEO4J_URI','bolt://127.0.0.1:7687'),
        auth=(os.getenv('NEO4J_USER','neo4j'),os.environ['NEO4J_PASSWORD']),
        connection_timeout=5, max_transaction_retry_time=10)

if __name__=='__main__':
    database=os.environ['NEO4J_DATABASE']
    source=(Path(__file__).parent/'schema.cypher').read_text(encoding='utf-8')
    source='\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('//'))
    with driver() as db,db.session(database=database) as session:
        for statement in source.split(';'):
            if statement.strip():session.run(statement).consume()
        session.run('CALL db.awaitIndexes(120)').consume()
    print('Schema initialized in '+database)
