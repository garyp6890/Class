"""Milestone interface contract; runtime engine is connected in the next stage."""
from typing import Protocol
from fastapi import FastAPI,HTTPException
from schemas import GraphRAGQueryRequest,GraphRAGResponse

class QAEngine(Protocol):
    def query(self,request:GraphRAGQueryRequest)->GraphRAGResponse:...

def create_app(engine:QAEngine|None=None):
    app=FastAPI(title='CTI GraphRAG checkpoint')
    @app.get('/health')
    def health():return {'status':'ready' if engine else 'design_checkpoint','engine_ready':engine is not None}
    @app.post('/query',response_model=GraphRAGResponse)
    def query(request:GraphRAGQueryRequest):
        if engine is None:raise HTTPException(503,'QA engine not connected in milestone checkpoint')
        return engine.query(request)
    return app
app=create_app()
