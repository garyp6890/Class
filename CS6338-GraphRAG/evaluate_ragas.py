"""Run only after real answers/contexts are saved. Separate evaluation environment."""
import json,argparse
from pathlib import Path

def main():
    from ragas import evaluate,EvaluationDataset,RunConfig
    from ragas.metrics import Faithfulness,ResponseRelevancy,LLMContextRecall,FactualCorrectness
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_ollama import ChatOllama,OllamaEmbeddings
    p=argparse.ArgumentParser();p.add_argument('responses');p.add_argument('--judge',default='qwen2.5:14b')
    p.add_argument('--output',default='results/ragas.csv');p.add_argument('--seed',type=int);a=p.parse_args()
    rows=json.loads(Path(a.responses).read_text(encoding='utf-8'))
    if a.seed is not None:rows=[r for r in rows if r.get('seed')==a.seed]
    required={'user_input','response','retrieved_contexts','reference'}
    if not rows or any(not required<=r.keys() for r in rows):raise ValueError('Missing RAGAS fields')
    llm=LangchainLLMWrapper(ChatOllama(model=a.judge,base_url='http://127.0.0.1:11434',temperature=0,num_ctx=8192,num_predict=2048))
    emb=LangchainEmbeddingsWrapper(OllamaEmbeddings(model='nomic-embed-text:v1.5',base_url='http://127.0.0.1:11434'))
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    import pandas as pd
    completed=pd.read_csv(out).to_dict('records') if out.exists() else []
    if len(completed)>len(rows):raise ValueError('Existing output belongs to a different evaluation cohort')
    for old,new in zip(completed,rows):
        if any(old.get(k)!=new.get(k) for k in ('id','seed','mode')):
            raise ValueError('Existing output row identity differs from requested cohort')
    for index,row in enumerate(rows):
        if index<len(completed):continue
        try:
            result=evaluate(EvaluationDataset.from_list([{k:row[k] for k in required}]),
                metrics=[Faithfulness(),ResponseRelevancy(strictness=1),LLMContextRecall(),FactualCorrectness()],llm=llm,embeddings=emb,
                run_config=RunConfig(timeout=180,max_retries=1,max_workers=1),raise_exceptions=False)
            record=result.to_pandas().to_dict('records')[0]
        except Exception as error:record={'error':type(error).__name__+': '+str(error)}
        record.update(row_index=index,id=row.get('id'),mode=row.get('mode'),seed=row.get('seed'))
        completed.append(record);pd.DataFrame(completed).to_csv(out,index=False)
        print(f'RAGAS {index+1}/{len(rows)} saved',flush=True)

if __name__=='__main__':main()
