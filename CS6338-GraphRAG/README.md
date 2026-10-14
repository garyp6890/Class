# CTI GraphRAG - Milestone 2

Garyad Passmore | CS 6338 Knowledge Engineering | Dr. Erdogan Dogdu

Design checkpoint for the Cyber Threat Intelligence GraphRAG Assistant for Incident Response.
The report describes the intended complete system. This checkpoint implements the models,
parser, resolver, chunker, extraction adapter, ingestion functions, schema initialization,
embedding helpers, retrieval primitives and evaluation scripts. The end-to-end QA engine and
frontend are still to be connected. `/query` returns HTTP 503 until an engine is supplied.
No extraction accuracy, RAGAS score, latency result or external benchmark score is claimed.

## Quick check (Python 3.11+)

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python validate_benchmark.py
```

The tests exercise invalid directions, fabricated evidence, unknown IDs, extra fields,
confidence boundaries, alias collisions, offsets, metric behavior, retrieval fusion,
request limits and source/path integrity. Passing them does not establish semantic accuracy.

## Database and models

Install Neo4j 5.26 with a dedicated empty project database. Set `NEO4J_URI`, `NEO4J_USER`,
`NEO4J_PASSWORD` and `NEO4J_DATABASE` in the local environment, then run `python init_db.py`.
Do not commit credentials. `schema.cypher` is idempotent and inserts no benchmark edges.
Use `ingest.ingest` inside `session.execute_write` with a GraphChunk, raw response and
the identity catalog. Only accepted, validated relations become assertions/edges.

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text:v1.5
uvicorn api:app --host 127.0.0.1 --port 8000
```

`extract.extract(chunk, catalog)` calls Ollama with JSON Schema and two repair attempts.
It does not load STIX relationship labels or gold answers. The provided extraction input
is `data/documents.json`; `data/entities.json` provides identity/type/alias context.
`embeddings.py` rejects overlength text rather than silently truncating it. Keep chunk
boundaries/IDs stable if a rejected input is split and reprocessed.

## Benchmark

The frozen ATT&CK 19.2 subset has 60 narrative records, 50 entities, 60 reference triples,
and 22 two-hop QA pairs (20 test, 2 development). There are 12 development and 48 test
extraction records. See `data/dataset_info.json` for the scope and limitations.
Reference labels are derived from official STIX and checked for structural integrity;
they still need student review of textual entailment. In particular, `gold-038` uses an
official USES label whose narrative says MagicRAT is associated with Lazarus operations.
Keep this disagreement visible during review; do not silently relabel it to improve scores.
`data/annotation_review.csv` provides a review worksheet.

All 20 test questions require a group-to-technique link and a technique-to-mitigation link.
The two development questions instead follow group-to-software-to-technique paths.
These are deliberately bounded, in-corpus reference questions, not a broad incident-response
benchmark. Entities and source records can overlap across question splits.

To rebuild from the official full release: `python build_benchmark.py path/to/enterprise-attack-19.2.json`.
Without a path, the script downloads that fixed release. Rebuilding resets review status.

## Evaluation after implementation

Save accepted predictions as a JSON list containing document_id, source_id, predicate,
target_id and evidence_text. Run `python evaluate_triples.py predictions.json --split test`.
Scoring deduplicates exact directed tuples per document. Wrong direction is both FP and FN.
Other-pair predictions in a scored record count as FP because this task targets its designated
endpoint pair. Omitted/quarantined records remain FN. Report review/quarantine rates separately.

For RAGAS, use a separate environment with `requirements-eval.txt`, pull `qwen2.5:14b`
and `nomic-embed-text`, and run `python evaluate_ragas.py responses.json`.
Each response row must contain user_input, response, retrieved_contexts (list of strings),
and reference. Run separately for text-only and hybrid outputs; preserve query IDs alongside
the files. Judge failures raise an error rather than being written as zero scores.
The local 14B judge is a planned configuration, subject to available memory, not an executed run.

## Related work and professor feedback

The design report includes a targeted review of CTINexus, AttacKG, CTIBench, TRAM and recent
CTI GraphRAG studies. CTI-ATE is the first proposed external test; its technique-ID F1 must
be kept separate from this project's exact triple F1 and multi-hop QA scores. The broad idea
of CTI GraphRAG is established; any paper contribution must depend on measured results and
a more specific gap. Primary links and search limitations are listed in `research_sources.json`.

## Checkpoint publication

Repository checkpoint: https://github.com/garyp6890/Class/tree/main/CS6338-GraphRAG

Submit this folder URL with `report/Passmore_GraphRAG_DesignDoc.pdf`.
The ZIP is a convenience copy of the source and report.

## Attribution

This project uses MITRE ATT&CK. The source subset retains official record identifiers,
descriptions and citations. See `data/source/MITRE_LICENSE.txt` and
https://attack.mitre.org/resources/terms-of-use/ . Third-party reports cited by ATT&CK retain
their own rights. Research references are cited, not redistributed as full papers here.
