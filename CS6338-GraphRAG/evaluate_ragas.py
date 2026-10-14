"""Run only after real answers/contexts are saved. Separate evaluation environment."""
import json,argparse
from pathlib import Path

def main():
    from ragas import evaluate,EvaluationDataset,RunConfig
    from ragas.metrics import Faithfulness,ResponseRelevancy,LLMContextRecall
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_ollama import ChatOllama,OllamaEmbeddings
    p=argparse.ArgumentParser();p.add_argument('responses');p.add_argument('--judge',default='qwen2.5:14b')
    p.add_argument('--output',default='results/ragas.csv');a=p.parse_args()
    rows=json.loads(Path(a.responses).read_text(encoding='utf-8'))
    required={'user_input','response','retrieved_contexts','reference'}
    if not rows or any(not required<=r.keys() for r in rows):raise ValueError('Missing RAGAS fields')
    llm=LangchainLLMWrapper(ChatOllama(model=a.judge,temperature=0,num_ctx=8192))
    emb=LangchainEmbeddingsWrapper(OllamaEmbeddings(model='nomic-embed-text'))
    result=evaluate(EvaluationDataset.from_list([{k:r[k] for k in required} for r in rows]),
        metrics=[Faithfulness(),ResponseRelevancy(),LLMContextRecall()],llm=llm,embeddings=emb,
        run_config=RunConfig(timeout=180,max_retries=2,max_workers=1),raise_exceptions=True)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    result.to_pandas().to_csv(out,index=False)

if __name__=='__main__':main()
