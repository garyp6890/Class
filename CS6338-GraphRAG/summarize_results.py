"""Aggregate saved observations without replacing failed runs with zero scores."""
import csv, json, statistics
from pathlib import Path
from run_pipeline import read,save,OUT,ROOT

def percentile(values,p):
    if not values:return None
    v=sorted(values);i=(len(v)-1)*p;lo=int(i);hi=min(lo+1,len(v)-1)
    return v[lo]+(v[hi]-v[lo])*(i-lo)

def main():
    from evaluate_triples import key
    if (OUT/'extraction.json').exists():
        extraction=read(OUT/'extraction.json');gold=read(ROOT/'data/gold_triples.json')
        predictions=read(OUT/'predictions.json')
        truth={key(r):r for r in gold};pred={key(r):r for r in predictions}
        from collections import Counter
        save(OUT/'extraction_error_analysis.json',{
            'false_negatives':[truth[k] for k in sorted(truth.keys()-pred.keys())],
            'false_positives':[pred[k] for k in sorted(pred.keys()-truth.keys())],
            'validation_error_counts':dict(Counter(e for r in extraction for e in r.get('errors',[]))),
            'attempt_counts':dict(Counter(str(r.get('attempts','exhausted')) for r in extraction)),
            'total_elapsed_seconds':sum(r['elapsed_ms'] for r in extraction)/1000,
            'note':'All records shown; split-specific headline metrics remain in extraction_metrics.json.'})
    rows=[r for p in sorted(OUT.glob('benchmark_[0-9][0-9].json')) for r in read(p)]
    summaries=[]
    for seed in (42,43,44,'pooled'):
        for mode in ('text_only','hybrid_without_node2vec','hybrid'):
            group=[r for r in rows if r['mode']==mode and (seed=='pooled' or r['seed']==seed)]
            ok=[r for r in group if 'error' not in r]
            def mean(key):return statistics.mean(r[key] for r in ok) if ok else None
            summaries.append({'seed':seed,'mode':mode,'attempted':len(group),'completed':len(ok),'errors':len(group)-len(ok),
                'evidence_recall':mean('evidence_recall'),'path_id_coverage':mean('path_ids_mentioned'),
                'citation_id_validity':statistics.mean(r['trace']['citation_ids_valid'] for r in ok) if ok else None,
                'abstention_rate':statistics.mean(r['status']=='insufficient_evidence' for r in ok) if ok else None,
                'retrieval_p95_ms':percentile([r['trace']['retrieval_ms'] for r in ok],.95),
                'total_p50_ms':percentile([r['execution_time_ms'] for r in ok],.5),
                'total_p95_ms':percentile([r['execution_time_ms'] for r in ok],.95)})
    save(OUT/'benchmark_summary.json',summaries)
    if summaries:
        with (OUT/'benchmark_summary.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    ragas=[{k:r[k] for k in ('id','seed','mode','user_input','response','retrieved_contexts','reference')} for r in rows if 'error' not in r]
    save(OUT/'ragas_input.json',ragas)
    with (OUT/'human_review.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['id','seed','mode','factuality_1_5','completeness_1_5','coherence_1_5','notes'])
        w.writerows([r['id'],r['seed'],r['mode'],'','','',''] for r in rows if 'error' not in r)
    print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
