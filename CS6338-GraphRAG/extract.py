"""Ollama adapter. It reads a chunk and entity catalog, never gold triples."""
import json,urllib.request,urllib.error
from pathlib import Path
from schemas import Extraction
from parser import parse_extraction

def extract(chunk,catalog,model='llama3.1:8b',base_url='http://localhost:11434'):
    prompt=(Path(__file__).parent/'prompts/extract.txt').read_text(encoding='utf-8')
    messages=[{'role':'system','content':prompt}, {'role':'user','content':json.dumps({
        'chunk_id':chunk.chunk_id,'catalog':list(catalog.values()),'text':chunk.text})}]
    errors=[]
    for attempt in range(3):
        body={'model':model,'messages':messages,'format':Extraction.model_json_schema(),
              'stream':False,'options':{'temperature':0,'seed':42,'num_ctx':8192,'num_predict':2500}}
        request=urllib.request.Request(base_url+'/api/chat',data=json.dumps(body).encode(),
            headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=120) as response:envelope=json.load(response)
        except (urllib.error.URLError,TimeoutError) as error:
            errors.append(type(error).__name__)
            continue
        raw=envelope['message']['content']
        try:
            if envelope.get('done_reason')=='length':raise ValueError('Truncated response')
            return parse_extraction(raw,chunk.text,catalog)
        except ValueError as error:
            errors.append(str(error))
            messages.extend([{'role':'assistant','content':raw},{'role':'user','content':
                f'Repair JSON using only the same input text. Error: {error}'}])
    return {'status':'quarantined','chunk_id':chunk.chunk_id,'errors':errors}
