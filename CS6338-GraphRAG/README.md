# CTI GraphRAG final capstone

Garyad Passmore | CS 6338 Knowledge Engineering | Dr. Erdogan Dogdu

An executable local Cyber Threat Intelligence GraphRAG assistant over a frozen
MITRE ATT&CK 19.2 subset. The final extends the original Milestone 2 checkpoint.

## Measured final run

All 60 narratives were processed. Test extraction precision **0.970**, recall **0.667**, F1 **0.790**; 17 records were quarantined across the full corpus.

Neo4j contains 43 accepted assertions, 60 chunks, and 50 canonical entities. Repeated ingestion preserved counts and deliberate rollback succeeded. GDS PageRank/WCC and 50 Node2Vec vectors of dimension 128 were executed for each seed. All 180 benchmark requests completed without API/output-validation errors.

| Mode | Evidence recall | Local judge factual F1 (finite n) | Total p95 (s) |
| --- | ---: | ---: | ---: |
| Text only | 0.675 | 0.246 (20) | 1.07 |
| Hybrid without Node2Vec | 0.625 | 0.413 (20) | 1.14 |
| Hybrid | 0.600 | 0.383 (20) | 1.04 |

The local judge covers all 20 questions in all three modes for seed 42. Full hybrid evidence recall is lower than text-only; no retrieval improvement is claimed. Valid citation membership is enforced by the engine and does not establish factual correctness. See the retained reg-save/mitigation failure case in the report.

All 18 automated tests pass. No human ratings or external CTIBench scores are claimed.

## Submission materials

- `report/Passmore_GraphRAG_FinalReport.pdf`: final technical report
- `report/Passmore_GraphRAG_FinalSlides.pptx`: 11-slide presentation
- `report/Passmore_GraphRAG_DemoScript.txt`: 5-7 minute demonstration script
- `results/`: actual extraction outputs, ingestion checks, GDS results, vectors,
  per-question traces, evaluation scores, timings, and recorded failures
- `report/Passmore_GraphRAG_DesignDoc.pdf`: preserved Milestone 2 design

## Scope and evidence boundary

The frozen corpus has 60 narratives and 50 canonical entities. Extraction has
12 development and 48 test records. QA has 20 test and two development questions.
The STIX-derived reference labels are **silver**, pending independent human review.
`gold-038` retains the documented MagicRAT/Lazarus USES-versus-association ambiguity.
No human ratings are invented; `results/human_review.csv` is a blank worksheet.

Structured STIX metadata is ingested separately as `STIXRelation` records and an
RDFLib Turtle mapping. Only accepted **text-extracted** domain relationships enter
QA retrieval or the GDS projection. Reference answers are never read by the engine.
The supplied Record context headers disclose endpoint identities: this is a
catalog-assisted, endpoint-conditioned extraction task, not open-world discovery.

## Local setup

Use Python 3.11+ and a dedicated Neo4j Community 5.26.x database. The measured run
uses Neo4j 5.26.4 with GDS 2.13.3 and APOC 5.26.4. Add compatible GDS/APOC JARs to
`plugins/`, then restart. n10s is not required: this implementation uses GDS and
explicit LPG traversal rather than OWL inference. APOC is available but not called.
Do not load this experiment into an unrelated database.

Add these settings to `conf/neo4j.conf`:

```properties
server.default_listen_address=127.0.0.1
server.memory.heap.initial_size=512m
server.memory.heap.max_size=2g
server.memory.pagecache.size=512m
dbms.security.procedures.unrestricted=gds.*,apoc.*
dbms.security.procedures.allowlist=gds.*,apoc.*
db.transaction.timeout=5s
```

From this folder in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
$env:NEO4J_URI='bolt://127.0.0.1:7687'
$env:NEO4J_USER='neo4j'
$env:NEO4J_PASSWORD='<your dedicated database password>'
$env:NEO4J_DATABASE='neo4j'
ollama pull llama3.1:8b
ollama pull nomic-embed-text:v1.5
ollama pull qwen2.5:14b
```

Start Neo4j and `ollama serve` before the execution stages. Model tags can change:
`results/manifest.json` records the actual downloaded digests and package versions.
The observed machine has 64 GB system memory and an NVIDIA RTX 5080 with 16 GB VRAM.

## Reproduce the experiment

The committed results are observations, not fixtures. To create a new run, **archive
or rename the existing results directory first**; extraction, benchmark, and RAGAS
stages resume existing artifacts and deliberately do not silently overwrite them.
Use the unchanged corpus, prompts, thresholds, and defaults for paired comparisons.

```powershell
python -m unittest discover -s tests -v
python validate_benchmark.py
python run_pipeline.py extract
python run_pipeline.py load
foreach ($seed in 42,43,44) {
  python run_pipeline.py analytics --seed $seed
  python run_pipeline.py benchmark --seed $seed
}
python summarize_results.py
python run_pipeline.py manifest
```

`extract` invokes the local model for all 60 narratives, saves each raw attempt,
validates and confidence-gates results, then scores exact directed tuples against
the 12/48 reference split. There are three total attempts per chunk, including the
initial request; network failures and JSON repairs share that budget. Exhausted
records are quarantined, retained, and counted as missing predictions.

`load` applies constraints, imports STIX metadata, revalidates raw extraction outputs,
loads accepted assertions, repeats ingestion to test idempotency, deliberately aborts
a transaction to verify rollback, writes 768-D text vectors, and checks indexes.
Review/rejected/quarantined relations are not promoted into the evidence graph.

`analytics` projects only accepted entity relationships as unweighted/undirected,
runs PageRank and WCC, and fits GDS Node2Vec (128 dimensions; walk length 30;
80 walks/node; return factor 1; in/out factor 0.5; window 5; negative samples 5;
20 iterations; concurrency 1). It exports vectors and procedure measurements.
The embedding-fit call has an explicit 300-second ceiling; ingestion retains the
five-second default transaction limit.

`benchmark` executes all 20 test questions under `text_only`,
`hybrid_without_node2vec`, and `hybrid`. Each seed gets its corresponding fitted
graph vectors. All modes use the same generator, prompt, evidence budget, and defaults.
The full plan has 180 requests. Raw generation, packed text, graph facts, resolved
anchors, source documents, latency, abstention, and explicit error rows are saved.
A structural neighbor proposes candidates; it never becomes relation evidence.

## API and interactive demonstration

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for an interactive query form, or:

```powershell
$body=@{
  query='In this frozen subset, which mitigation is linked to Software Packing (T1027.002) as reported for APT29, and what is the two-edge evidence path?'
  mode='hybrid'
} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/query -Method Post -ContentType 'application/json' -Body $body
```

The default app connects `LiveQAEngine`; it no longer has the unwired 503 route.
Generation uses short local citations such as `[C1]`. Each returned citation contains
that label plus the immutable full chunk ID, document ID, URL, and evidence text.
`/health` checks populated text embeddings and required model availability.
Dependency or invalid-output errors return 502. API schema failures return 422.
These are preserved failures, not successful abstentions or invented answers.
`api_wiring_pilot_42.json` preserves the preliminary long-ID wiring failure and is
excluded from the final experiment. The prompt and short-label mapping were then
frozen for all 180 final benchmark attempts. The extraction instrumentation pilot is
also retained separately; it does not enter the reported extraction score.
The API is the demonstration interface; a separate Streamlit frontend is not required.
`results/api_smoke.json` verifies real HTTP routing and serialization, not answer
accuracy: its development answer names T1048.002 where the reference expects T1005.
That unsuccessful answer is preserved. `results/demo_query.json` retains a separate
live QA-05 response with the supported Software Packing -> Heuristic-based malware
detection path and citations C1/C2, matching the demonstration script.

## Evaluation and interpretation

`benchmark_summary.csv` reports per-seed and pooled evidence recall, citation-ID
membership, abstention, path-ID coverage, errors, and latency. Evidence recall uses
the **packed** source documents. Path-ID coverage is a lexical diagnostic, not
answer accuracy. Citation membership is not proof of claim-level entailment.
Membership validity is enforced by the response gate, so 100% validity among
accepted responses is a structural property rather than an independent quality win.
Timing includes model loading when it occurs; the runs do not establish controlled
warm-model latency. Repeated questions across seeds are not independent samples.

Run the local judge in a separate environment:

```powershell
python -m venv .eval-venv
.eval-venv/Scripts/python -m pip install -r requirements-eval.txt
.eval-venv/Scripts/python evaluate_ragas.py results/ragas_input.json --seed 42 --output results/ragas.csv
```

`results/eval_environment.txt` records the resolved judge-environment versions and
can be used as a lockfile in a fresh evaluation environment.

RAGAS 0.2.15 uses local qwen2.5:14b at temperature zero for faithfulness, context
recall, response relevancy, and reference-based factual correctness (F1).
Relevancy strictness is 1 (a documented cost control),
and the judge cohort is all 20 questions under all three modes for seed 42. The full
180-run benchmark still receives deterministic local evaluation. This bounded judge
audit avoids repeatedly judging the same questions across seeds. Remove `--seed 42`
to evaluate additional seeds in a new output file.
Judge context is 8,192, output ceiling 2,048, and worker count 1. Each row is saved before
continuing. Missing/non-finite metrics and exceptions stay missing, with their
finite-score denominators reported. RAGAS is an automated judge, not human evidence.

## Limitations and deferred work

- Small, template-based in-corpus QA; possible entity/source overlap across splits.
- STIX silver labels and endpoint context make extraction easier than open-world CTI.
- Exact evidence substrings do not establish semantic entailment by themselves.
- Ambiguous aliases stay in review unless an explicit canonical ID disambiguates them.
- Positive-question benchmark does not establish unanswerable-question detection.
- No external CTIBench, production deployment, or independently collected human scores.
- No claimed improvement unless the measured paired results support it.

Related-work links and the original bibliography remain in `research_sources.json`.
MITRE attribution is retained in `data/source/MITRE_LICENSE.txt`.
