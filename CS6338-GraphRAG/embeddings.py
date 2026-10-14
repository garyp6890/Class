"""Text embedding adapter and seeded Node2Vec walks. No gold-data loading."""
import json,urllib.request,random,hashlib,math

def text_embedding(text,is_query=False,base_url='http://localhost:11434'):
    prefix='search_query: ' if is_query else 'search_document: '
    body={'model':'nomic-embed-text:v1.5','input':prefix+text,'truncate':False}
    req=urllib.request.Request(base_url+'/api/embed',data=json.dumps(body).encode(),
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as response:vector=json.load(response)['embeddings'][0]
    if len(vector)!=768 or not all(math.isfinite(x) for x in vector):raise ValueError('Invalid text vector')
    norm=math.sqrt(sum(x*x for x in vector))
    if not norm:raise ValueError('Zero vector')
    return [x/norm for x in vector]

def node2vec_walks(adjacency,num_walks=80,length=30,p=1.0,q=.5,seed=42):
    if p<=0 or q<=0:raise ValueError('p and q must be positive')
    rng=random.Random(seed);nodes=sorted(adjacency);walks=[]
    for _ in range(num_walks):
        starts=nodes.copy();rng.shuffle(starts)
        for start in starts:
            walk=[start]
            while len(walk)<length:
                neighbors=sorted(adjacency[walk[-1]])
                if not neighbors:break
                previous=walk[-2] if len(walk)>1 else None
                weights=[1 if previous is None else 1/p if n==previous else
                         1 if n in adjacency[previous] else 1/q for n in neighbors]
                walk.append(rng.choices(neighbors,weights=weights,k=1)[0])
            walks.append(walk)
    return walks

def graph_embeddings(adjacency,seed=42):
    from gensim.models import Word2Vec
    stable_hash=lambda word:int(hashlib.md5(word.encode()).hexdigest()[:8],16)
    model=Word2Vec(sentences=node2vec_walks(adjacency,seed=seed),vector_size=128,
        window=5,min_count=1,sg=1,negative=5,epochs=20,workers=1,seed=seed,
        sample=0,hashfxn=stable_hash)
    return {n:model.wv.get_vector(n,norm=True).tolist() for n in adjacency if adjacency[n]}
