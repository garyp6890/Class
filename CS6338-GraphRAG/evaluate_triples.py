"""Micro exact-match extraction metrics; document and edge direction matter."""
import json,argparse
from pathlib import Path

def key(row):
    return (row['document_id'],row.get('subject_id',row.get('source_id')),
            row['predicate'],row.get('object_id',row.get('target_id')))

def score(gold,predictions):
    truth={key(r) for r in gold};predicted={key(r) for r in predictions}
    tp=len(truth&predicted);fp=len(predicted-truth);fn=len(truth-predicted)
    p=tp/(tp+fp) if tp+fp else 0.0;r=tp/(tp+fn) if tp+fn else 0.0
    return dict(tp=tp,fp=fp,fn=fn,precision=p,recall=r,f1=2*p*r/(p+r) if p+r else 0.0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('predictions');p.add_argument('--split',choices=['development','test'],default='test')
    a=p.parse_args();root=Path(__file__).parent
    gold=[x for x in json.loads((root/'data/gold_triples.json').read_text(encoding='utf-8')) if x['split']==a.split]
    docs={x['document_id'] for x in gold}
    # Exclude the other split. An output within a scored record with a wrong endpoint is a false positive.
    pred=[x for x in json.loads(Path(a.predictions).read_text(encoding='utf-8')) if x['document_id'] in docs]
    metrics={'split':a.split,'micro':score(gold,pred),'by_predicate':{k:score([x for x in gold if x['predicate']==k],
        [x for x in pred if x['predicate']==k]) for k in sorted({x['predicate'] for x in gold+pred})}}
    print(json.dumps(metrics,indent=2))
