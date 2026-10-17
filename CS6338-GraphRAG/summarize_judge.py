"""Summarize finite local judge scores with explicit denominators."""
import csv,math,statistics
from run_pipeline import OUT,save

def main():
    rows=list(csv.DictReader((OUT/'ragas.csv').open(encoding='utf-8')))
    metrics=('faithfulness','answer_relevancy','context_recall','factual_correctness')
    summaries=[]
    for mode in ('text_only','hybrid_without_node2vec','hybrid','pooled'):
        subset=rows if mode=='pooled' else [r for r in rows if r.get('mode')==mode]
        entry={'mode':mode,'attempted':len(subset)}
        for metric in metrics:
            values=[]
            for row in subset:
                try:
                    v=float(row.get(metric,row.get(metric+'(mode=f1)','')))
                    if math.isfinite(v):values.append(v)
                except (ValueError,TypeError):pass
            entry[metric]={'finite':len(values),'missing':len(subset)-len(values),
                           'mean':statistics.mean(values) if values else None}
        summaries.append(entry)
    save(OUT/'ragas_summary.json',summaries)
    with (OUT/'ragas_summary.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['mode','attempted','metric','finite','missing','mean'])
        for row in summaries:
            for metric in metrics:
                v=row[metric];w.writerow([row['mode'],row['attempted'],metric,v['finite'],v['missing'],v['mean']])
    print(summaries)
if __name__=='__main__':main()
