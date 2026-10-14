# CTI GraphRAG - Milestone 2

Garyad Passmore | CS 6338 Knowledge Engineering | Dr. Erdogan Dogdu

Design and code checkpoint for the **Cyber Threat Intelligence GraphRAG Assistant for Incident Response**.
Read the [10-page design report](report/Passmore_GraphRAG_DesignDoc.pdf) for the architecture and evaluation plan.

## Assignment deliverables

| Deliverable | Location |
| --- | --- |
| Database schema and initialization | [schema.cypher](schema.cypher), [init_db.py](init_db.py) |
| Extraction prompt and strict parser | [prompts/extract.txt](prompts/extract.txt), [parser.py](parser.py) |
| 60 reference triples | [data/gold_triples.json](data/gold_triples.json) |
| 22 two-hop QA pairs | [data/eval_queries.json](data/eval_queries.json) |
| Source narratives and entity catalog | [data/documents.json](data/documents.json), [data/entities.json](data/entities.json) |

## What is implemented

- Pydantic data models, chunking, alias resolution and extraction validation.
- Ollama extraction adapter, Neo4j schema/ingestion functions and inverse-rule query.
- Text embedding and Node2Vec helpers, bounded retrieval templates and rank fusion.
- Reference-data validation, exact-triple scoring and a RAGAS evaluation adapter.

The 12 unit tests pass. These checks cover parser rejection cases, confidence boundaries,
alias collisions, chunk offsets, scoring, request limits, fusion and reference integrity.
Live Neo4j/model integration and end-to-end performance have not been verified.

## What is stubbed or planned

The QA engine and Streamlit frontend still need to be connected. `api.py` defines the
interface; `/health` reports `design_checkpoint` and `/query` returns HTTP 503 until an
engine is supplied. No extraction accuracy, RAGAS score or latency result is claimed.

## Run the checkpoint tests

From this `CS6338-GraphRAG` folder, with Python 3.11+:

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install "pydantic>=2.8,<3"
python -m unittest discover -s tests -v
python validate_benchmark.py
```

These tests do not require Neo4j, Ollama or downloaded model weights.
For implementation work, install `requirements.txt`. Use a dedicated Neo4j 5.26 database;
set `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` and `NEO4J_DATABASE`, then run `python init_db.py`.
The planned local models are `llama3.1:8b` and `nomic-embed-text:v1.5`.

## Benchmark scope and review

The frozen ATT&CK 19.2 subset contains 60 narrative records, 50 entities and 60 reference
triples (12 development / 48 extraction test). The 22 QA pairs contain 20 test and two
development questions. See [dataset notes](data/dataset_info.json) and the
[annotation review worksheet](data/annotation_review.csv).

Labels come from official STIX and pass structural checks; student review of textual
entailment remains pending. In `gold-038`, the official USES label is stronger than the
MagicRAT/Lazarus narrative's association wording. Preserve and adjudicate this discrepancy.
The questions are narrow and template-based, and splits may share entities/source records.
Gold labels and reference answers must remain outside the extraction and retrieval inputs.

## Remaining work for the final milestone

1. Review the reference annotations and resolve ambiguous labels before freezing the benchmark.
2. Run extraction, retain errors/review decisions, and verify Neo4j ingestion and vector indexes.
3. Connect retrieval, citation validation, answer generation and the frontend.
4. Compare text-only, hybrid and hybrid-without-Node2Vec conditions on the frozen questions.
5. Report triple P/R/F1, evidence retrieval, RAGAS, human ratings, latency and unsuccessful cases.
6. Run CTIBench CTI-ATE as a separate external evaluation after the core experiment.

Use `python evaluate_triples.py predictions.json --split test` for real extraction outputs.
For RAGAS, use a separate environment with `requirements-eval.txt` and run
`python evaluate_ragas.py responses.json`; each row needs `user_input`, `response`,
`retrieved_contexts` and `reference`. The local judge configuration is described in the report.

## Related work and attribution

The report distinguishes peer-reviewed AttacKG, CTINexus and CTIBench from TRAM tooling
and the newer CTI GraphRAG preprints. [Research sources](research_sources.json) retain the links.
This project uses MITRE ATT&CK; see the [MITRE license](data/source/MITRE_LICENSE.txt)
and [ATT&CK terms](https://attack.mitre.org/resources/terms-of-use/).

Submission repository: https://github.com/garyp6890/Class/tree/main/CS6338-GraphRAG
