"""Behavioral contracts: actual generation must stay behind the evidence boundary."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from schemas import GraphRAGQueryRequest,GraphRAGResponse,SubgraphContext
from api import create_app

class FinalTests(unittest.TestCase):
    def test_collision_resolved_only_by_explicit_context_id(self):
        from resolve import resolve
        cat=[dict(id='G1',name='Fox',entity_type='ThreatGroup',aliases=['Shared']),
             dict(id='G2',name='Bear',entity_type='ThreatGroup',aliases=['Shared'])]
        self.assertEqual(resolve('Shared','ThreatGroup',cat)['status'],'review')
        self.assertEqual(resolve('Shared','ThreatGroup',cat,['G2'])['id'],'G2')
    def test_live_adapter_called_for_ablation(self):
        class Engine:
            def query(self,request):
                self.request=request
                return GraphRAGResponse(answer='Evidence missing',status='insufficient_evidence',citations=[],
                    retrieved_subgraph=SubgraphContext(),execution_time_ms=1)
        engine=Engine();client=TestClient(create_app(engine))
        response=client.post('/query',json={'query':'Where is the evidence?','mode':'hybrid_without_node2vec'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(engine.request.mode,'hybrid_without_node2vec')
    def test_dependency_failure_is_not_fabricated_answer(self):
        class Engine:
            def query(self,request):raise OSError('unavailable')
        response=TestClient(create_app(Engine())).post('/query',json={'query':'What is APT29?'})
        self.assertEqual(response.status_code,502)
        self.assertNotIn('answer',response.json())
    def test_api_rejects_excess_hops(self):
        self.assertEqual(TestClient(create_app()).post('/query',json={'query':'APT29','max_hop_distance':9}).status_code,422)
    def test_zero_walk_bias_rejected(self):
        from embeddings import node2vec_walks
        with self.assertRaises(ValueError):node2vec_walks({'a':{'b'},'b':{'a'}},p=0)
    def test_generated_unknown_citation_is_rejected(self):
        import io,json
        from unittest.mock import MagicMock
        from engine import LiveQAEngine
        session=MagicMock()
        session.run.side_effect=[[],[{'chunk_id':'c1','text':'evidence','score':1}],
            [{'chunk_id':'c1','text':'evidence','document_id':'d1','source_url':'https://example.org'}]]
        db=MagicMock();db.session.return_value.__enter__.return_value=session
        opened=MagicMock();opened.__enter__.return_value=io.StringIO(json.dumps({
            'message':{'content':json.dumps({'answer':'Claim [invented]','status':'answered','cited_chunk_ids':['invented']})}}))
        with patch('engine.driver') as factory,patch('engine.text_embedding',return_value=[0.0]*768),patch('engine.urllib.request.urlopen',return_value=opened):
            factory.return_value.__enter__.return_value=db
            with self.assertRaisesRegex(ValueError,'invalid citations'):
                LiveQAEngine().query(GraphRAGQueryRequest(query='Which evidence?',mode='text_only'))

if __name__=='__main__':unittest.main()
