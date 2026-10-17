"""HTTP interface for the live Neo4j/Ollama engine."""
from typing import Protocol
from fastapi import FastAPI,HTTPException
from neo4j.exceptions import Neo4jError,DriverError
from schemas import GraphRAGQueryRequest,GraphRAGResponse

class QAEngine(Protocol):
    def query(self,request:GraphRAGQueryRequest)->GraphRAGResponse:...

def create_app(engine:QAEngine|None=None):
    if engine is None:
        from engine import LiveQAEngine
        engine=LiveQAEngine()
    app=FastAPI(title='CTI GraphRAG')
    @app.get('/health')
    def health():
        return engine.health() if hasattr(engine,'health') else {'status':'ready','engine_ready':True}
    @app.post('/query',response_model=GraphRAGResponse)
    def query(request:GraphRAGQueryRequest):
        try:return engine.query(request)
        except (OSError,RuntimeError,ValueError,KeyError,Neo4jError,DriverError) as error:
            raise HTTPException(502,'Live QA dependency or output validation failed') from error
    return app
app=create_app()
