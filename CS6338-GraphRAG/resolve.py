import re
from difflib import SequenceMatcher

def normalize(name):
    return re.sub(r'[^a-z0-9]+',' ',name.casefold()).strip()

def resolve(name, entity_type, catalog, context_ids=None):
    options=[x for x in catalog if x['entity_type']==entity_type]
    exact=[x for x in options if name.upper()==x['id'] or normalize(name) in
           {normalize(n) for n in [x['name'],*x['aliases']]}]
    if len(exact)==1:return {'status':'resolved','id':exact[0]['id'],'method':'ID/name/alias'}
    if len(exact)>1:
        supported=[x for x in exact if x['id'] in (context_ids or [])]
        if len(supported)==1:
            return {'status':'resolved','id':supported[0]['id'],'method':'alias plus explicit context ID'}
        return {'status':'review','candidates':[x['id'] for x in exact]}
    ranked=sorted([(max(SequenceMatcher(None,normalize(name),normalize(n)).ratio()
        for n in [x['name'],*x['aliases']]),x['id']) for x in options],reverse=True)
    if ranked and ranked[0][0]>=0.92 and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=0.08):
        return {'status':'review','candidates':[ranked[0][1]],'similarity':ranked[0][0]}
    return {'status':'unresolved','candidates':[x[1] for x in ranked[:3]]}
