"""Editable report source. Requires reportlab; outputs the 10-page design PDF."""
from pathlib import Path
import json,csv,re
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Preformatted,Flowable
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).parent
OUT=ROOT/'report';OUT.mkdir(exist_ok=True)
FONT=Path('C:/Windows/Fonts')
if (FONT/'arial.ttf').exists():
    for name,file in [('Body','arial.ttf'),('Bold','arialbd.ttf'),('Italic','ariali.ttf')]:pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
    pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Italic',boldItalic='Bold')
    pdfmetrics.registerFont(TTFont('Mono',str(FONT/'consola.ttf')))
else:
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    for name,base in [('Body','Helvetica'),('Bold','Helvetica-Bold'),('Italic','Helvetica-Oblique')]:
        pdfmetrics.registerFont(pdfmetrics.Font(name,base,'WinAnsiEncoding'))
    registerFontFamily('Body',normal='Body',bold='Bold',italic='Italic',boldItalic='Bold')
    pdfmetrics.registerFont(pdfmetrics.Font('Mono','Courier','WinAnsiEncoding'))
NAVY=colors.HexColor('#19364C');TEAL=colors.HexColor('#277A83');PALE=colors.HexColor('#EDF3F6')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('B',fontName='Body',fontSize=10,leading=13.6,spaceAfter=7,textColor=NAVY))
styles.add(ParagraphStyle('SmallB',parent=styles['B'],fontSize=8.6,leading=11.3,spaceAfter=5))
styles.add(ParagraphStyle('H',fontName='Bold',fontSize=17,leading=21,textColor=NAVY,spaceAfter=13))
styles.add(ParagraphStyle('Sub',fontName='Bold',fontSize=11,leading=14,textColor=TEAL,spaceBefore=6,spaceAfter=6))
styles.add(ParagraphStyle('TitleB',fontName='Bold',fontSize=23,leading=27,textColor=NAVY,spaceAfter=12))
styles.add(ParagraphStyle('Cell',parent=styles['B'],fontSize=8.5,leading=11,spaceAfter=0))
styles.add(ParagraphStyle('CodeB',fontName='Mono',fontSize=8.2,leading=9.6,spaceAfter=8,textColor=NAVY))
story=[]
def p(t,small=False):story.append(Paragraph(t,styles['SmallB' if small else 'B']))
def h(t):story.append(Paragraph(escape(t),styles['H']))
def sub(t):story.append(Paragraph(escape(t),styles['Sub']))
def code(t):story.append(Preformatted(t,styles['CodeB']))
def page():story.append(PageBreak())
def table(rows,widths=None,compact=False):
    formatted=[[Paragraph(re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)', '&amp;',str(c)),styles['Cell']) for c in row] for row in rows]
    t=Table(formatted,colWidths=widths or [524/len(rows[0])]*len(rows[0]),hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LINEBELOW',(0,0),(-1,0),.8,TEAL),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#CDD8DF')),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),2 if compact else 5),('BOTTOMPADDING',(0,0),(-1,-1),2 if compact else 5)]))
    story.append(t);story.append(Spacer(1,9))
def link(url,label):return f'<link href="{escape(url)}" color="#277A83">{escape(label)}</link>'

class Architecture(Flowable):
    def __init__(self):Flowable.__init__(self);self.width=524;self.height=226
    def draw(self):
        c=self.canv
        items=[('ATT&CK narrative records','Frozen descriptions + identity catalog'),
               ('Chunker -> LLM extractor -> Validator','1,800 characters / 200 overlap; strict JSON'),
               ('Entity resolver -> Neo4j','Canonical entities + assertions + source chunks'),
               ('Text encoder + Node2Vec -> vector indexes','768-D text / 128-D graph, separate spaces'),
               ('Hybrid retrieval -> Answer generator','Text matches + supported 1-2 hop paths'),
               ('FastAPI -> Streamlit analyst view','Answer, source citations, graph and latency')]
        for i,(title,detail) in enumerate(items):
            y=190-i*37
            c.setFillColor(PALE);c.setStrokeColor(TEAL);c.roundRect(0,y,360,32,5,stroke=1,fill=1)
            c.setFillColor(NAVY);c.setFont('Bold',9.7);c.drawString(10,y+20,title)
            c.setFont('Body',8.2);c.drawString(10,y+9,detail)
            if i<5:
                c.setStrokeColor(TEAL);c.line(180,y,180,y-5);c.line(177,y-2,180,y-5);c.line(183,y-2,180,y-5)
        c.setFillColor(PALE);c.setStrokeColor(NAVY);c.roundRect(378,109,146,106,5,stroke=1,fill=1)
        for j,line in enumerate(['Reference evaluation','60 STIX-derived triples','22 two-hop QA pairs','Read by scorers only','No gold edges sent to','extractor or retrieval']):
            c.setFillColor(NAVY);c.setFont('Bold' if j==0 else 'Body',8.5);c.drawString(386,199-15*j,line)
        c.setFont('Body',8);c.drawString(381,74,'UI sends query requests');c.drawString(381,62,'to the retrieval engine.');c.drawString(381,38,'Offline graph building');c.drawString(381,26,'precedes online QA.')

class Classes(Flowable):
    def __init__(self):Flowable.__init__(self);self.width=524;self.height=103
    def draw(self):
        c=self.canv
        for x,title,detail in [(0,'QueryRequest','query, mode, k, hops'),(180,'QAEngine','query(request)'),(360,'QueryResponse','answer, citations, graph')]:
            c.setFillColor(PALE);c.setStrokeColor(TEAL);c.roundRect(x,52,164,44,4,stroke=1,fill=1)
            c.setFillColor(NAVY);c.setFont('Bold',10);c.drawString(x+7,79,title);c.setFont('Body',8);c.drawString(x+7,64,detail)
        for x in [164,344]:c.line(x,74,x+16,74);c.line(x+12,78,x+16,74);c.line(x+12,70,x+16,74)
        c.setFont('Body',8.8);c.drawString(0,29,'GraphChunk -> SourceDocument; Assertion -> Entity (subject/object) + GraphChunk (evidence)')
        c.drawString(0,12,'QAEngine composes Resolver, TextIndex, GraphRetriever and AnswerGenerator.')

# Page 1
story.append(Paragraph('Cyber Threat Intelligence<br/>GraphRAG Assistant',styles['TitleB']))
p('<b>System Architecture &amp; Design Document | Milestone 2</b>')
p('Garyad Passmore<br/>CS 6338: Knowledge Engineering<br/>Professor: Dr. Erdogan Dogdu<br/>October 14, 2026')
sub('1. Executive Summary & System Requirements')
p('The system will help an incident responder connect threat groups, software, ATT&amp;CK techniques and mitigations, then inspect the evidence behind each answer. The main comparison is whether combining graph paths with text retrieval improves two-hop answers over text-only RAG when both systems use the same source text and local language model.')
p('The implementation stays within the approved CTI proposal. Its first corpus is a frozen MITRE ATT&amp;CK Enterprise 19.2 subset: 60 relationship narratives covering APT29, APT28, FIN7 and Lazarus Group, with 50 canonical entities. Campaigns remain supported by the schema but are absent from this initial subset. The source release is fixed so later ATT&amp;CK edits do not change the comparison. [T1]')
table([['Requirement','Acceptance condition'],
['Evidence-backed answers','Return a directed one- or two-hop path and citations for its necessary links; state when evidence is missing.'],
['Extraction and resolution','Validate JSON, type/direction, canonical IDs and verbatim evidence; retain review and rejected outputs.'],
['Fair comparison','Use identical corpus, text embeddings, generator, prompt and context budget for text-only and hybrid modes.'],
['Performance targets','For one concurrent warm-model user: retrieval p95 under 1 s and complete answer p95 under 30 s. Measure hardware, cold starts and timeouts separately. These are targets, not results.'],
['Practical operation','Local Ollama and Neo4j; cache by input plus model/corpus version; process writes in batches of 100 and measure throughput. No paid API is required.']],[112,412])
p('<b>Checkpoint status.</b> Data preparation and validation utilities are implemented. The end-to-end QA service, database/model integration tests and comparative experiments remain implementation work. No accuracy or latency result is claimed in this design document.',small=True)
p('<b>Professor feedback.</b> The related-work review on page 10 identifies existing CTI graph systems and ATT&amp;CK evaluation resources. A conference paper is a possible later outcome, conditional on a narrower contribution and credible results.',small=True)

# Page 2
page();h('2. End-to-End System Architecture')
story.append(Architecture());story.append(Spacer(1,8))
p('Figure 1. The offline pipeline prepares the evidence store; the online pipeline answers questions. Reference labels are kept outside the runtime retrieval path.')
table([['Connection','Payload and protocol'],
['Source -> chunker','Local UTF-8 JSON: narrative text, record ID, source URL and release. Keep original text and character offsets.'],
['Chunker -> extractor','Python GraphChunk -> local Ollama HTTP POST /api/chat. Identity catalog is allowed; STIX predicates and reference answers are withheld.'],
['Extractor -> resolver/store','Validated Pydantic objects -> exact ID/name/alias lookup -> transactional Neo4j Bolt writes. Low-confidence facts enter a separate review queue.'],
['Store -> embedders','Chunk text to Ollama /api/embed; accepted domain edges to Node2Vec. Write vectors back through Bolt.'],
['UI -> retrieval/generator','HTTP JSON POST /query -> bounded, parameterized Cypher and vector search -> Ollama /api/chat. Return structured answer and citations.'],
['Saved outputs -> evaluation','JSON response files -> exact-triple scorer, RAGAS and human rating sheet. No evaluator feedback is supplied to test-time generation.']],[129,395])
sub('Failure handling and experiment boundaries')
p('Malformed or truncated extraction responses receive at most two repair attempts. Network failures use the same three-attempt ceiling. Persist the original response and error before quarantining a record; an omitted record still counts against recall. A failed database transaction is retried without changing its stable assertion ID. Query-time database or model failures produce a service error, not an invented answer.')
p('The identity catalog makes this a catalog-assisted extraction task. Recovering relations from ATT&amp;CK narrative descriptions is also easier than extracting from arbitrary incident reports. External technique-mapping tests and later report-level evaluation are needed before making broader claims.',small=True)

# Page 3
page();h('3. Graph Extraction & Schema Engineering')
table([['Node / attributes','Role'],
['Entity: id, name, aliases, entity_type','Base label plus ThreatGroup, Software, Technique, Mitigation or Campaign. ATT&amp;CK external IDs are canonical; Software retains malware/tool subtype in the source catalog.'],
['SourceDocument: id, source_url','One source narrative record. Its release and record identifier remain available in documents.json.'],
['Chunk: id, text, start, end','Original text span plus text_embedding. SourceDocument -HAS_CHUNK-> Chunk.'],
['Assertion: id, predicate, confidence','One directed assertion per source record; SUBJECT and OBJECT point to entities. SUPPORTED_BY points to chunks and stores verbatim evidence.']],[210,314])
p('<b>Domain predicates.</b> USES permits ThreatGroup -> Software/Technique and Software -> Technique. MITIGATED_BY is Technique -> Mitigation, reversing the original STIX mitigates direction. ASSOCIATED_WITH permits ThreatGroup -> Campaign/Software and does not imply use. MENTIONED_IN links entities to their source documents; MENTIONS_ENTITY links chunks to entities.')
sub('Chunking, structured output and prompt specification')
p('Use 1,800-character windows with 200-character overlap, never crossing records. Chunk IDs include the document ID and starting offset. Llama 3.1 8B runs locally at temperature 0, seed 42, context 8,192 and output cap 2,500 tokens. The Ollama format field receives Extraction.model_json_schema(); parser.py enforces the result. [T5]')
code('Extraction = {"entities": [Entity], "relations": [Relation]}\nEntity = {"id": str, "name": str, "entity_type": enum, "aliases": [str]}\nRelation = {"source_id": str, "target_id": str, "predicate": enum,\n            "evidence_text": str, "confidence": float[0,1]}')
p('The finalized prompt in prompts/extract.txt restricts output to catalog IDs and affirmative, text-supported claims. It rejects speculation, negation and co-occurrence. Record headers supply the two endpoint identities, not the predicate; extraction is limited to that designated pair. Three synthetic few-shot examples demonstrate normal USES edges, reversed mitigation wording and abstention:')
table([['Synthetic input','Required behavior'],['Night Fox uses Echo. Echo performs Data Capture.','GTEST USES STEST; STEST USES TTEST'],['Restrict Access mitigates Data Capture.','TTEST MITIGATED_BY MTEST'],['Night Fox has not been observed using Echo.','Return no relation.']],[302,222])
sub('Resolution and confidence')
p('Resolve unique, typed ID/name/alias matches automatically. After punctuation and case normalization, a string-similarity score at least 0.92 with a 0.08 margin proposes a candidate for review; it never forces a fuzzy merge. Alias collisions remain unresolved. Accept valid edges at confidence >= 0.85; review 0.60-0.85; reject below 0.60. These are initial development thresholds, and model confidence is not a calibrated probability.',small=True)
p('Verbatim evidence and valid types are necessary but do not prove entailment. Student review must check whether the quoted sentence actually supports the chosen predicate.',small=True)

# Page 4
page();h('4. Graph Storage, Enhancement & Reasoning')
p('Neo4j 5.26 stores both the domain graph and its provenance. Each accepted fact has a typed domain edge for traversal and an Assertion node for supporting text. This avoids trying to attach a relationship to another relationship. Multiple documents can support the same entity pair without erasing their separate evidence.')
code('CREATE CONSTRAINT entity_id IF NOT EXISTS\nFOR (n:Entity) REQUIRE n.id IS UNIQUE;\nCREATE CONSTRAINT assertion_id IF NOT EXISTS\nFOR (n:Assertion) REQUIRE n.id IS UNIQUE;\nCREATE CONSTRAINT chunk_id IF NOT EXISTS\nFOR (n:Chunk) REQUIRE n.id IS UNIQUE;\nCREATE CONSTRAINT document_id IF NOT EXISTS\nFOR (n:SourceDocument) REQUIRE n.id IS UNIQUE;')
p('schema.cypher also indexes Entity.name and assertion endpoint/predicate properties. init_db.py reads connection settings from environment variables, applies each statement and waits for indexes. ingest.py uses stable document/triple-derived IDs and MERGE inside a transaction, so replaying a chunk does not duplicate an assertion. The script validates the raw response again before writing.')
sub('Reasoning layer: an evidence-preserving inverse')
p('The rule USES(x,y) implies USED_BY(y,x) provides a reverse lookup without adding new claims. reasoning.cypher returns the same assertion and source chunk. Derived facts appear only in generator context; the response subgraph retains canonical edge directions, and extraction scoring excludes inferred views.')
code("MATCH (a:Assertion {predicate:'USES'})-[:SUBJECT]->(x:Entity)\nMATCH (a)-[:OBJECT]->(y:Entity)\nMATCH (a)-[:SUPPORTED_BY]->(c:Chunk)\nWHERE y.id = $entity_id\nRETURN y.id AS subject_id, 'USED_BY' AS predicate,\n       x.id AS object_id, a.id AS assertion_id,\n       c.id AS chunk_id, true AS derived;")
p('USES is not transitive: a group using software and software having a capability does not establish that the group exercised that capability. The two links can be shown as a potential connection, with both sources, but cannot be collapsed into a new observed group-technique edge.')
sub('Extraction ground-truth verification')
p('evaluate_triples.py compares exact (document ID, subject ID, predicate, object ID) sets. Duplicate outputs count once; a reversed edge produces a false positive and a false negative. The endpoint-pair task is explicit: other-pair output in a scored record is a false positive. Quarantined or missing records remain false negatives rather than disappearing from the denominator.')
code('precision = TP / (TP + FP)     recall = TP / (TP + FN)\nF1 = 2 * precision * recall / (precision + recall)\npython evaluate_triples.py predictions.json --split test')
p('Report micro and per-predicate metrics, review rate and quarantine rate. The 12 development records support prompt/threshold changes; the 48 test records are scored after freezing those choices. Current reference labels come from official STIX, not successful model outputs. Their text-level review remains pending.',small=True)

# Page 5
page();h('5. Featurization, Embedding & Hybrid Indexing')
sub('Graph representation learning')
p('Build an unweighted, undirected projection of accepted canonical domain edges only. Exclude Chunk, Assertion and SourceDocument nodes so file structure does not dominate the walks. Keep directions and predicates in Neo4j for reasoning; the projection is only for Node2Vec similarity. [T2]')
p('For a walk that arrived at node v from t, the next neighbor x has probability proportional to alpha(t,x) times the edge weight. The return parameter p and exploration parameter q determine alpha:')
code('P(next=x | previous=t, current=v) = alpha(t,x) / sum_z alpha(t,z)\nalpha(t,x) = 1/p  if x=t;  1 if distance(t,x)=1;  1/q otherwise\nmaximize sum_u sum_v in N_S(u) log P(v | u)\nP(v | u) = exp(z_v dot z_u) / sum_w exp(z_w dot z_u)')
p('The objective predicts walk-context neighbors with skip-gram; five negative samples approximate the softmax. Initial settings are 128 dimensions, 80 walks per node, walk length 30, window 5, p=1, q=0.5, 20 epochs, seed 42 and one worker. The outward bias is a hypothesis for finding structurally related entities, not an assumption that it improves QA. Tune only on development data; skip graph-vector lookup for isolated nodes.')
sub('Separate text and graph spaces')
table([['Index','Encoder / payload','Query and interpretation'],
['chunk_text','nomic-embed-text:v1.5; 768-D Chunk.text_embedding','Encode the question with search_query: and text with search_document:. Cosine ranks text relevance.'],
['entity_graph','Node2Vec; 128-D Entity.graph_embedding','Look up the vector of a resolved anchor entity, then find nearby graph vectors. Similarity proposes candidates; it is not relation evidence.']],[83,203,238])
p('Text and graph vectors cannot be compared directly: they have different dimensions and training objectives. Hybrid retrieval combines ranked evidence lists, not the vectors themselves. Nomic is selected for local embedding; the adapter checks dimension, finite values and norm, and sets truncate=false so overlength inputs fail visibly. Split and reindex any rejected input with new offsets before testing. [T4, T5]')
code("CREATE VECTOR INDEX chunk_text IF NOT EXISTS\nFOR (n:Chunk) ON (n.text_embedding)\nOPTIONS {indexConfig: {`vector.dimensions`: 768,\n  `vector.similarity_function`: 'cosine'}};\nCREATE VECTOR INDEX entity_graph IF NOT EXISTS\nFOR (n:Entity) ON (n.graph_embedding)\nOPTIONS {indexConfig: {`vector.dimensions`: 128,\n  `vector.similarity_function`: 'cosine'}};")
p('Both indexes use Neo4j vector search. Rebuild graph embeddings when accepted edges change; invalidate cached results when the corpus or encoder changes. The planned ablation removes Node2Vec while retaining text retrieval and graph traversal to test whether graph similarity contributes anything on this small graph. [T3]',small=True)

# Page 6
page();h('6. Hybrid GraphRAG QA Engine & Prompts')
p('<b>Retrieval algorithm.</b> (1) Resolve explicit ATT&amp;CK IDs or unique aliases in the question. (2) Embed the query and retrieve 10 text candidates. (3) Expand resolved anchors through supported one- or two-hop domain paths. Optionally retrieve five Node2Vec neighbors per anchor, retaining only candidates with a supported path. (4) Fetch assertion evidence for every path edge. (5) Rank graph evidence by anchor coverage, then shorter paths, then mean edge confidence, with stable ID ties. (6) Fuse the resulting chunk list with text ranks and retain five evidence chunks within the context budget.')
code('RRF(chunk) = 1/(60 + text_rank) + 1/(60 + graph_rank)\n# A missing rank contributes zero; deduplicate chunk IDs first.\n# At most 40 nodes, 80 edges, 50 paths and 5 final chunks.\n# Reserve <= 6,000 input-context tokens in an 8,192-token model window.')
p('Merge overlapping spans from the same record before formatting. Keep a graph fact only when its supporting text is included; if trimming loses a required link, mark that path incomplete. An unresolved anchor falls back to text retrieval. No raw LLM-generated Cypher is executed: hop limits choose one of two allowlisted templates and values use parameters. The engine enforces a five-second database transaction timeout.')
sub('Exact answer-generator template')
prompt=(ROOT/'prompts/answer.txt').read_text(encoding='utf-8')
code(prompt)
p('Use Llama 3.1 8B at temperature 0, seed 42, with the same instructions and 250-word limit in both conditions. Text-only mode supplies an empty GRAPH list. Validate the JSON and verify that every returned citation ID belongs to the supplied context. Unsupported citation IDs trigger one repair attempt; continued failure returns insufficient_evidence. Citation presence alone does not establish factual correctness.')
p('<b>Analyst view.</b> Streamlit will display the answer, expandable source passages, the small directed subgraph, retrieval mode and elapsed time. The analyst can inspect evidence before applying an answer to an incident. Query-time reasoning is explanatory; this project does not execute response actions.',small=True)

# Page 7
page();h('7. Evaluation Pipeline & Benchmark Protocol')
p('The reference set contains 60 triples from 60 ATT&amp;CK narrative records. Twelve records are development data and 48 are extraction test data. QA includes 20 test questions and two development questions, each with two supporting edges and source IDs. Gold triples and QA references are available only to evaluation scripts, not the extractor, indexer or answer generator.')
sub('Paired experiment and automated metrics')
p('Freeze prompts and thresholds after development. Run text-only RAG and hybrid GraphRAG on the same 20 test questions with the same corpus, generator, text encoder, final chunk limit and context-token budget. Add a hybrid-without-Node2Vec ablation. Repeat the frozen conditions with seeds 42, 43 and 44; report paired per-question differences and variation, not just the best run. Evaluate cold and warm latency separately.')
table([['Measure','Configuration and interpretation'],
['Extraction P/R/F1','Exact directed tuple matching per source record, with micro and per-predicate values.'],
['RAGAS','ragas==0.2.15; Faithfulness, ResponseRelevancy, LLMContextRecall. Input: user_input, response, retrieved_contexts and reference. [T6]'],
['Judge and execution','Local qwen2.5:14b at T=0; nomic text embeddings for relevance; one worker, 180-second timeout, two retries. Run failures are errors, not zero scores.'],
['Evidence and latency','Count retrieval of both required source documents, unsupported claims, valid citations, abstentions and p50/p95 response time.'],
['External comparison','After the core experiment, run CTIBench CTI-ATE technique-ID extraction separately. Preserve its task/scorer; do not combine its F1 with triple or QA scores. [R3]']],[123,401])
sub('Human testing rubric')
p('Randomize answer order and hide the retrieval mode. Rate all 20 test answers per condition against the source passages. Garyad performs the initial review; seek a second reviewer for any later paper and report disagreements. The first review cannot be described as independent inter-rater validation.')
table([['Score','Factuality','Completeness','Coherence'],
['1','Mostly unsupported or wrong','Misses both links','Cannot follow the answer'],
['2','Major factual error','Only a fragment is covered','Major logical gaps'],
['3','Mixed support; needs correction','One link or key caveat missing','Understandable but uneven'],
['4','Supported with minor issue','Both links; minor omission','Clear with minor repetition'],
['5','All claims supported; uncertainty accurate','Both links, citations and needed limits','Direct, consistent and easy to follow']],[40,164,170,150])
p('<b>Limitations to preserve.</b> The questions are narrow and template-based; shared entities/records make this an in-corpus test, not evidence of generalization to unseen actors. Gold-038 has an official USES label but association wording, so it requires adjudication. Model self-confidence and an LLM judge can both be wrong. The dataset needs student text-level review before being described as manually reviewed gold.',small=True)

# Page 8
page();h('7. Evaluation Queries & Expected Paths')
p('The full questions, reference answers and two supporting document IDs are in data/eval_queries.json. For test rows 01-20, the question is: <i>In this frozen subset, which mitigation is linked to [technique] as reported for [group], and what is the two-edge evidence path?</i> The answer must establish Group USES Technique and Technique MITIGATED_BY Mitigation; naming the mitigation alone is incomplete.',small=True)
entities={e['id']:e for e in json.loads((ROOT/'data/entities.json').read_text(encoding='utf-8'))}
queries=json.loads((ROOT/'data/eval_queries.json').read_text(encoding='utf-8'))
rows=[['ID','Group','Technique','Expected mitigation']]
for q in queries[:20]:
    a,t,m=q['expected_path'];rows.append([q['id'][-2:],entities[a]['name'],f"{t} {escape(entities[t]['name'])}",f"{m} {escape(entities[m]['name'])}"])
table(rows,[27,75,213,209],compact=True)
p('<b>Development questions 21-22.</b> Which technique connects APT28 through LAMEHUG? Expected path: G0007 -> S9035 -> T1005. Which technique connects Lazarus Group through MagicRAT? Expected path: G0032 -> S1182 -> T1016. Both ask for evidence for each link; question 22 inherits the association-versus-use ambiguity and must be reviewed before tuning.',small=True)
p('<b>Rationale.</b> Each test query joins two separate narrative records, making missing-link retrieval visible. The software questions exercise a second path shape. These 22 QA pairs satisfy the checkpoint count but do not cover the diversity of real incident-response questions. Add unanswerable, conflicting-evidence and unseen-report cases before claiming broader performance.',small=True)

# Page 9
page();h('8. Software Interfaces & Data Models')
story.append(Classes());story.append(Spacer(1,6))
p('Figure 2. The query interface separates retrieval/generation from transport. The response contains the evidence needed to inspect the result. schemas.py supplies the complete Pydantic v2 models with extra fields forbidden.')
code("class Entity(StrictModel):\n    id: str\n    name: str\n    entity_type: EntityType\n    aliases: list[str] = Field(default_factory=list)\n\nclass Relation(StrictModel):\n    source_id: str\n    target_id: str\n    predicate: Literal['USES','MITIGATED_BY','ASSOCIATED_WITH']\n    evidence_text: str = Field(min_length=1)\n    confidence: float = Field(ge=0, le=1)\n\nclass GraphChunk(StrictModel):\n    chunk_id: str\n    document_id: str\n    text: str\n    start: int = Field(ge=0)\n    end: int = Field(ge=0)\n    source_url: str\n    # Validator checks end - start == len(text).\n\nclass GraphRAGQueryRequest(StrictModel):\n    query: str = Field(min_length=3, max_length=2000)\n    mode: Literal['text_only','hybrid'] = 'hybrid'\n    top_k_chunks: int = Field(default=5, ge=1, le=10)\n    max_hop_distance: int = Field(default=2, ge=1, le=2)\n    enable_reasoning_rules: bool = True")
table([['Endpoint','Contract'],['GET /health','200: service status and engine_ready flag. Current checkpoint reports design_checkpoint.'],['POST /query','Validated GraphRAGQueryRequest -> GraphRAGResponse. Invalid input: 422; engine not connected: 503; planned runtime timeout: 504.']],[104,420])
p('GraphRAGResponse includes answer, answered/insufficient_evidence status, citations with source URLs and passages, the retrieved subgraph, elapsed milliseconds and a UTC timestamp. api.py intentionally returns 503 until a QAEngine implementation is connected rather than returning demonstration answers as real results.')
p('<b>Verified checkpoint.</b> Twelve unit tests pass for parser rejection cases, confidence boundaries, alias collision, chunk offsets, scoring, request bounds, fusion and reference integrity. Neo4j writes, live LLM extraction, vector population, frontend integration and RAGAS execution are not yet verified. The repository includes executable adapters and templates for these next steps.',small=True)
p('<b>Repository checkpoint.</b> '+link('https://github.com/garyp6890/Class/tree/main/CS6338-GraphRAG','github.com/garyp6890/Class/tree/main/CS6338-GraphRAG')+'. The folder contains the code, prompts, schema, reference datasets and this report. A ZIP copy is also provided.',small=True)

# Page 10
page();h('Related Work & ATT&CK Benchmark Research')
p('The professor requested similar work and existing benchmarks. This targeted review found clear precedents for both CTI graph extraction and graph-based retrieval. A direct Google Scholar search was attempted but its results page was inaccessible; the papers and author-maintained resources below were checked directly. This is not an exhaustive literature review.',small=True)
table([['Work / resource','Relevance and decision for this project'],
['AttacKG [R1]','Extracts attack-behavior graphs and aggregates technique knowledge. Its extraction/technique evaluation is useful background; its published scores are not directly comparable to this smaller ontology or QA task.'],
['CTINexus [R2]','LLM triplet extraction, hierarchical entity alignment and distant-relation inference closely overlap the proposed extraction stage. Use it to motivate an extraction baseline; retain the simpler canonical-ID resolver for this milestone.'],
['CTIBench / CTI-ATE [R3]','The released CTI-ATE task has 60 ATT&CK technique-extraction examples, scored with F1. Best first external mapping test; it does not test group-to-technique-to-mitigation QA. Keep its labels, scorer and version assumptions separate.'],
['MITRE CTID TRAM [R4]','Open ATT&CK mapping platform with data and SciBERT notebooks; the repository describes coverage of up to 50 techniques. Useful mapping baseline/data source, but requires a report-level split and label-version checks.'],
['Beyond RAG for CTI [R5]','2026 preprint comparing vector, graph, agentic and hybrid retrieval across 3,300 CTI QA pairs. This is a direct precedent. Its linked artifacts are a candidate larger evaluation, subject to checking availability, licensing and question provenance.'],
['Operationalizing CTI with GraphRAG [R6]','2026 preprint comparing GraphRAG and vector retrieval for detection plans. The application overlaps incident response, but detection-plan robustness differs from evidence-backed QA; its results cannot be carried over.']],[124,400])
p('<b>Research direction.</b> ATT&amp;CK STIX is the source knowledge base, not an independent chatbot benchmark. Start with the paired local QA comparison and CTI-ATE; then test report-level holdouts, abstention and the Node2Vec ablation. A possible paper question is whether a local, evidence-constrained pipeline improves path completeness without increasing unsupported claims. The general claim that GraphRAG helps CTI is already studied, so a paper needs a more specific, measured contribution.',small=True)
sub('References and implementation sources')
refs=[
('R1','Li, Z., Zeng, J., Chen, Y., & Liang, Z. (2022). AttacKG: Constructing Technique Knowledge Graph from Cyber Threat Intelligence Reports.','https://arxiv.org/abs/2111.07093'),
('R2','Cheng, Y., et al. (2025). CTINexus: Automatic Cyber Threat Intelligence Knowledge Graph Construction Using Large Language Models. IEEE EuroS&P.','https://ctinexus.github.io/'),
('R3','Alam, M. T., et al. (2024). CTIBench: A Benchmark for Evaluating LLMs in Cyber Threat Intelligence. NeurIPS 37.','https://github.com/maveryn/cti-bench'),
('R4','Center for Threat-Informed Defense. (2023). Threat Report ATT&CK Mapper (TRAM).','https://github.com/center-for-threat-informed-defense/tram'),
('R5','Hamzic, D., et al. (2026). Beyond RAG for Cyber Threat Intelligence: A Systematic Evaluation of Graph-Based and Agentic Retrieval. Preprint.','https://arxiv.org/abs/2604.11419'),
('R6','Kabra, A., Paliwal, P., & Hanawal, M. K. (2026). Operationalizing Cyber Threat Intelligence with GraphRAG. Preprint.','https://arxiv.org/abs/2608.13050')]
for rid,title,url in refs:p(f'[{rid}] {escape(title)} '+link(url,'Source'),small=True)
research=json.loads((ROOT/'research_sources.json').read_text(encoding='utf-8'))
p('Technical sources: '+'; '.join(f"[{s['id']}] "+link(s['url'],s['title']) for s in research['sources'] if s['id'].startswith('T'))+'. Accessed October 14, 2026. Full URLs are retained in research_sources.json.',small=True)

def footer(canvas,doc):
    canvas.setStrokeColor(TEAL);canvas.setLineWidth(.6);canvas.line(44,753,568,753)
    canvas.setFont('Body',8);canvas.setFillColor(NAVY);canvas.drawString(44,763,'CS 6338  |  GRAPH RAG SYSTEM DESIGN')
    canvas.setStrokeColor(colors.HexColor('#CDD8DF'));canvas.line(44,37,568,37)
    canvas.drawString(44,24,'Garyad Passmore  |  Milestone 2');canvas.drawRightString(568,24,str(doc.page))

dest=OUT/'Passmore_GraphRAG_DesignDoc.pdf'
doc=SimpleDocTemplate(str(dest),pagesize=(612,792),leftMargin=44,rightMargin=44,topMargin=52,bottomMargin=48,
    title='CTI GraphRAG Assistant - System Architecture & Design',author='Garyad Passmore')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
gold=json.loads((ROOT/'data/gold_triples.json').read_text(encoding='utf-8'))
worksheet=ROOT/'data/annotation_review.csv'
if not worksheet.exists():
    with worksheet.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['id','subject_id','predicate','object_id','evidence_text','review_status','reviewer','notes'])
        for row in gold:w.writerow([row['id'],row['subject_id'],row['predicate'],row['object_id'],row['evidence_text'],'pending','',
            'Official USES label; narrative expresses association. Adjudicate.' if row['id']=='gold-038' else ''])
print(dest)
