# Architecture

_Status: draft · Last updated: 2026-10-17_

This folder describes the target architecture of open-rag-engine across all five phases. It zooms in level by level, from the system in its environment down to interfaces and data. Detailed decisions live in [`../adr/`](../adr/), and per-phase work lives in [`../plans/`](../plans/).

Components are tagged with the phase that delivers them (**P1** to **P5**), so the same pages double as the roadmap.

## Reading order

| # | Document | Level | Answers |
| --- | --- | --- | --- |
| 01 | [Context](01-context.md) | System | Who uses the system and what it talks to |
| 02 | [Containers](02-containers.md) | Deployable units | Which processes and stores exist and how they connect |
| 03 | [Components](03-components.md) | Inside each container | Which services and modules live in each process |
| 04 | [Layers](04-layers.md) | Code organisation | How the code is layered and which way dependencies point |
| 05 | [Interfaces](05-interfaces.md) | Contracts | The `Protocol`s every swappable part implements |
| 06 | [Domain model](06-domain-model.md) | Data | Domain objects, their invariants and the database schema |
| 07 | [Ingestion](07-ingestion.md) | Runtime flow | How a file becomes searchable chunks |
| 08 | [Query](08-query.md) | Runtime flow | How a question becomes a cited answer, plus caching and fallbacks |
| 09 | [Evaluation](09-evaluation.md) | Runtime flow | How quality is measured, gated and diagnosed |
| 10 | [Security](10-security.md) | Cross-cutting | Trust boundaries, access control, injection defences |
| 11 | [Deployment](11-deployment.md) | Operations | Local compose setup and the scaled 10M-document design |

New readers should read 01, 02 and 08. Contributors adding a component should read 04 and 05.

## Principles

1. **Every stage is a swappable part behind an interface.** Ingestion, chunking, embedding, retrieval, fusion, reranking, generation and citation are each defined by a `Protocol`. Implementations are chosen in YAML config, never in code.
2. **Every stage can be toggled and measured.** The query pipeline is assembled from config, so the eval harness can switch any stage on or off and compare against the baseline. That is how ablations work.
3. **Security happens at retrieval time.** Tenant and access filters are applied inside the store query, before ranking. The LLM never sees a chunk the user cannot read.
4. **Every answer is traceable.** Each request carries a trace id, and every stage records its inputs, outputs, scores and timings as a span.
5. **Degrade, don't fail.** When a dependency is down, the system answers with less (BM25 only, no reranking, a fallback LLM) and says so in the response.
6. **Dependencies point inward.** Domain models and interfaces depend on nothing. Adapters depend on interfaces. Entry points wire everything together.
7. **Data is immutable.** Domain objects are frozen. Pipeline stages return new state instead of mutating it, which is what makes per-stage debug snapshots free.

## Phase map

| Phase | Adds to the architecture |
| --- | --- |
| P1 Baseline | Domain, interfaces, config, parsers, fixed and recursive chunkers, fastembed, pgvector, dense retriever, LLM adapters, citation mapper, API with SSE and debug flag, CLI, docker compose |
| P2 Evaluation | Eval runner, datasets, metrics, LLM judge and calibration, citation verifier, failure classifier, CI gate |
| P3 Retrieval quality | Postgres full-text BM25, RRF fusion, cross-encoder reranker, query rewriting, structure-aware and semantic chunkers, parent/child chunks |
| P4 Production hardening | Worker and queue with DLQ, Redis caches, OpenTelemetry and dashboards, auth, rate limits, ACL and tenant enforcement, PII redaction, injection suite, fallbacks, load tests, scaling note |
| P5 Launch | Demo UI, hosted demo, README results table, write-up, v1.0 release |

## Conventions for these docs

- Diagrams are Mermaid, so they render on GitHub and diff cleanly in reviews.
- Dashed boxes or edges mean optional or switchable.
- When code and docs disagree, the code wins and the doc gets fixed in the same pull request.
