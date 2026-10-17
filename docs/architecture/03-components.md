# 03 · Components

What lives inside each application process. The API, worker and CLI share the same core library; they differ only in which entry point and services they run.

```mermaid
flowchart TB
    subgraph API["API container"]
        direction TB
        mw["Middleware · P1/P4<br/>request id, auth, rate limit, RequestContext"]
        r_query["Query routes · P1<br/>POST /query, SSE"]
        r_docs["Document routes · P4<br/>POST/DELETE /documents"]
        r_fb["Feedback route · P4<br/>POST /feedback"]
        r_ops["Ops routes · P1/P4<br/>/healthz, /metrics"]
        qs["QueryService"]
        mw --> r_query
        mw --> r_docs
        mw --> r_fb
        r_query --> qs
    end

    subgraph Worker["Worker container · P4"]
        consumer["Job consumer<br/>retries, backoff, DLQ"]
        is["IngestionService"]
        consumer --> is
    end

    subgraph Eval["CLI process · ore eval · P2"]
        er["AblationRunner"]
        scorers["Metric scorers + LLM judge"]
        classifier["Failure classifier"]
        reporter["Report writer"]
        er --> scorers --> classifier --> reporter
    end

    subgraph Core["Shared core library"]
        pf["PipelineFactory<br/>builds stages from config"]
        stages["Query stages<br/>transform, retrieve, fuse, rerank,<br/>build context, generate, cite, verify"]
        ingest_parts["Ingestion parts<br/>parsers, chunkers, embedder"]
        repos["Stores<br/>DocumentRepository, VectorStore, KeywordIndex"]
        llm["LLM adapters"]
        cache["Caches · P4"]
        tracer["Tracer + metrics"]
    end

    qs --> pf --> stages
    stages --> repos
    stages --> llm
    stages --> cache
    is --> ingest_parts
    is --> repos
    r_docs -->|"enqueue"| consumer
    er --> qs
    stages -.-> tracer
    is -.-> tracer
```

## Component catalogue

| Component | Container | Responsibility | Phase |
| --- | --- | --- | --- |
| Middleware | API | Assigns a request id, authenticates the API key, applies rate limits, builds the `RequestContext` (tenant, access tags, debug flag) | P1 (request id), P4 (auth, limits) |
| Query routes | API | Validates input, calls `QueryService`, serialises JSON or SSE | P1 |
| Document routes | API | Uploads and deletes documents by enqueueing ingestion jobs | P4 |
| Feedback route | API | Stores thumbs up/down against a query log row | P4 |
| `QueryService` | API, CLI | Runs the pipeline for one question; owns caching and fallback policy | P1 |
| `PipelineFactory` | Core | Reads config, resolves each stage from the registry, wraps every stage with tracing and timing | P1 |
| Query stages | Core | One class per stage, each implementing `Stage` (see [05](05-interfaces.md)) | P1 to P3 |
| `IngestionService` | CLI, Worker | Hash, diff, parse, chunk, embed and write one document transactionally | P1 |
| Job consumer | Worker | Pulls jobs, retries with backoff, moves poison jobs to the DLQ | P4 |
| `AblationRunner` | CLI | Runs a dataset against a matrix of configs | P2 |
| Metric scorers and judge | CLI | Retrieval, generation, citation, safety and system metrics | P2 |
| Failure classifier | CLI | Assigns each wrong answer to one failure class | P2 |
| Report writer | CLI | Writes versioned JSON and Markdown reports | P2 |

## Why one shared core

`ore eval` calls the same `QueryService` as the API, with a config override. The code being measured is exactly the code being shipped, so an ablation result can't be an artefact of a separate eval-only code path.
