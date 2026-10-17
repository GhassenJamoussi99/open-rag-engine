# 08 · Query

How a question becomes a cited answer. `QueryService` runs a sequence of stages that `PipelineFactory` assembles from config. Dashed stages are optional and can be switched off per request or per eval run.

## Pipeline

```mermaid
flowchart LR
    q["Query + RequestContext"] --> cache{"Answer cache hit? · P4"}
    cache -->|"yes"| out["Answer"]
    cache -->|"no"| rewrite["Query rewrite and<br/>multi-query · P3"]
    rewrite --> dense["Dense retriever · P1"]
    rewrite --> bm25["BM25 retriever · P3"]
    dense --> fuse["RRF fusion · P3"]
    bm25 --> fuse
    fuse --> rerank["Cross-encoder rerank · P3"]
    rerank --> ctx["Context builder<br/>parent expansion, token budget"]
    ctx --> gen["Generator · P1<br/>grounded prompt, refusal"]
    gen --> cite["Citation mapper · P1"]
    cite --> verify["Citation verifier · P2"]
    verify --> out

    classDef optional stroke-dasharray: 5 5
    class cache,rewrite,bm25,fuse,rerank,verify optional
```

| Stage | Reads from state | Adds to state | Phase |
| --- | --- | --- | --- |
| Transform | `query` | `variants` (rewritten and expanded queries) | P3 |
| Retrieve | `variants`, `context` | `candidates` per retriever | P1 |
| Fuse | `candidates` | one fused list | P3 |
| Rerank | fused list | `ranked` top-n | P3 |
| Build context | `ranked` | parent-expanded chunks within the token budget | P1 |
| Generate | context chunks | `prompt`, raw answer | P1 |
| Cite | raw answer, context chunks | `answer` with `citations` | P1 |
| Verify | `answer` | a verdict on each citation | P2 |

Each stage takes the state and returns a new one. Because the state is immutable, the debug response can return a snapshot after every stage: candidates and scores before and after reranking, the final prompt and the timings.

## Sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant A as API
    participant S as QueryService
    participant K as Cache
    participant R as Retrievers
    participant P as Postgres
    participant X as Reranker
    participant L as LLM
    participant T as Tracer

    C->>A: POST /query with API key
    A->>A: authenticate, rate limit, build RequestContext
    A->>S: answer(query, context)
    S->>T: start trace
    S->>K: lookup(query, tenant, config hash)
    alt cache hit
        K-->>S: cached answer
    else cache miss
        S->>R: retrieve(query variants, filters)
        R->>P: ANN search and BM25 search, tenant and ACL filters applied in SQL
        P-->>R: candidate chunks with scores
        R-->>S: fused candidates
        S->>X: rerank(query, candidates)
        X-->>S: top-k chunks
        S->>L: stream(grounded prompt)
        L-->>A: tokens, relayed as SSE token events
        S->>S: map and verify citations
        S->>K: store answer
    end
    S->>T: end trace with all spans
    S-->>A: answer, citations, trace id, degraded flags
    A-->>C: final SSE event with citations
```

## Grounding and citations

- The prompt numbers each context chunk (`[1]`, `[2]`, …) inside clear delimiters and says the content is data, not instructions.
- The model must cite with `[n]` markers or answer that the evidence is missing.
- The citation mapper keeps only markers that point to a chunk in the prompt and resolves each to document, pages and character span.
- The answer is refused, without calling the LLM, when no candidate scores above `refusal_min_score`.
- An answer that is not refused but has no valid citation is returned flagged `uncited`, never hidden.

## API contract

```json
{
  "answer": "The agreement is governed by the laws of Delaware [1].",
  "refused": false,
  "uncited": false,
  "degraded": [],
  "trace_id": "4bf92f3577b34da6",
  "citations": [
    {"marker": 1, "chunk_id": "…", "document_id": "…", "title": "…",
     "page_start": 12, "page_end": 12, "char_start": 40211, "char_end": 40388,
     "quote": "…", "verdict": "supported"}
  ],
  "debug": {"stages": [{"name": "retrieve", "candidates": [{"chunk_id": "…", "score": 0.83}], "ms": 14}], "prompt": "…"}
}
```

SSE streams send `token` events while the answer is generated, then one `citations` event and one `done` event. Citations come last because they can only be resolved once the full answer is known. `debug` is present only when the request sets `debug: true` and the key is allowed to use it.

## Caching (P4)

| Tier | Key | Stores | Invalidated by |
| --- | --- | --- | --- |
| Query embedding | model + normalized query | Vector | Embedding model change |
| Retrieval results | normalized query + filters + config hash + index version | Ranked chunk ids | Index version bump on ingest |
| Semantic answer | query embedding similarity above a threshold, within one tenant and access-tag set | Answer + citations | Index version bump, TTL |

Every cache key includes the tenant and access tags, so a cache can never return an answer across permissions.

## Reliability and fallbacks (P4)

Each dependency has a timeout, retries with exponential backoff and a fallback. When a fallback is used, the response lists it in `degraded` and the span records it.

```mermaid
flowchart TD
    start["Query"] --> vs{"Vector search OK?"}
    vs -->|"yes"| hyb["Hybrid candidates"]
    vs -->|"timeout or down"| bm["BM25 only<br/>degraded: vector_store"]
    hyb --> rr{"Reranker OK within budget?"}
    bm --> rr
    rr -->|"yes"| top["Reranked top-k"]
    rr -->|"no"| fused["Fused order<br/>degraded: reranker"]
    top --> llm1{"Primary LLM OK?"}
    fused --> llm1
    llm1 -->|"yes"| ans["Answer"]
    llm1 -->|"no"| llm2{"Fallback LLM OK?"}
    llm2 -->|"yes"| ans2["Answer<br/>degraded: llm_fallback"]
    llm2 -->|"no"| err["503 with retrieved sources<br/>so the user can still read them"]
```

## Configuration

One YAML file describes a full pipeline. Its hash is stored on every query log row and every eval report, so any number can be reproduced.

```yaml
pipeline:
  query_transform: null          # P3: {name: multi_query, n: 3}
  retrievers: [dense]            # P3: [dense, bm25]
  fusion: null                   # P3: {name: rrf, k: 60}
  reranker: null                 # P3: {name: bge-reranker, top_n: 8}
  context: {max_tokens: 6000, expand_parents: false}
  generator: {provider: anthropic, refusal_min_score: 0.35, timeout_s: 30}
  fallback_generator: null       # P4
store: {name: pgvector, hnsw: {m: 16, ef_construction: 64, ef_search: 40}}
```
