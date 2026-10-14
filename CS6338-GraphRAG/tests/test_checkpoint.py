import unittest,json
from schemas import GraphRAGQueryRequest
from parser import parse_extraction
from resolve import resolve
from chunking import chunk_document
from evaluate_triples import score
from validate_benchmark import validate
from retrieval import rrf

class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.cat={'G1':{'id':'G1','name':'Fox','entity_type':'ThreatGroup','aliases':['F']},
                  'S1':{'id':'S1','name':'Echo','entity_type':'Software','aliases':[]}}
        self.row={'entities':list(self.cat.values()),'relations':[{'source_id':'G1','target_id':'S1',
            'predicate':'USES','confidence':.9,'evidence_text':'Fox uses Echo.'}]}
    def parse(self):return parse_extraction(json.dumps(self.row),'Fox uses Echo.',self.cat)
    def test_valid(self):self.assertEqual(len(self.parse()['accepted']),1)
    def test_direction(self):
        self.row['relations'][0].update(source_id='S1',target_id='G1')
        with self.assertRaises(ValueError):self.parse()
    def test_fabricated_evidence(self):
        self.row['relations'][0]['evidence_text']='Fox uses invented malware.'
        with self.assertRaises(ValueError):self.parse()
    def test_unknown_id(self):
        self.row['entities'][0]['id']='G999'
        with self.assertRaises(ValueError):self.parse()
    def test_extra_field(self):
        self.row['unexpected']=True
        with self.assertRaises(ValueError):self.parse()
    def test_thresholds(self):
        for confidence,bucket in [(0.59,'rejected'),(.60,'review'),(.849,'review'),(.85,'accepted')]:
            self.row['relations'][0]['confidence']=confidence
            self.assertEqual(len(self.parse()[bucket]),1)
    def test_alias_collision(self):
        cat=list(self.cat.values())+[{'id':'G2','name':'Bear','entity_type':'ThreatGroup','aliases':['F']}]
        self.assertEqual(resolve('F','ThreatGroup',cat)['status'],'review')
    def test_chunk_offsets(self):
        text='abc'*1400;chunks=chunk_document({'document_id':'d','text':text,'source_url':'https://example.org'})
        for c in chunks:self.assertEqual(c.text,text[c.start:c.end])
        self.assertEqual(chunks[0].text[-200:],chunks[1].text[:200])
        self.assertEqual(chunks[-1].end,len(text))
    def test_metrics_reverse_and_omission(self):
        g=[dict(document_id='d',subject_id='G1',predicate='USES',object_id='S1')]
        p=[dict(document_id='d',subject_id='S1',predicate='USES',object_id='G1')]
        self.assertEqual(score(g,p)['fp'],1);self.assertEqual(score(g,p)['fn'],1)
        self.assertEqual(score(g,[])['recall'],0);self.assertEqual(score(g,g+g)['tp'],1)
    def test_bounds(self):
        with self.assertRaises(ValueError):GraphRAGQueryRequest(query='test',max_hop_distance=3)
    def test_rrf(self):self.assertEqual(rrf(['a','b','a'],['b','c'])[0],'b')
    def test_reference_integrity(self):self.assertEqual(validate()['test_qa'],20)

if __name__=='__main__':unittest.main()
