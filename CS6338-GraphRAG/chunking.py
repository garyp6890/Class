from schemas import GraphChunk

def chunk_document(document, size=1800, overlap=200):
    if not 0<=overlap<size:raise ValueError('Require 0 <= overlap < size')
    text=document['text'];out=[];start=0
    while start<len(text):
        end=min(start+size,len(text))
        out.append(GraphChunk(chunk_id=f"{document['document_id']}:{start}",
            document_id=document['document_id'],text=text[start:end],start=start,end=end,
            source_url=document['source_url']))
        if end==len(text):break
        start=end-overlap
    return out
