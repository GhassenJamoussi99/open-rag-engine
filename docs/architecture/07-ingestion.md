# 07 · Ingestion

How a source file becomes searchable chunks. `IngestionService.ingest(source_uri)` is the single entry point; the CLI calls it directly in P1, and the queue worker calls it in P4.

## Flow

```mermaid
flowchart LR
    src["Source file"] --> hash["Hash content"]
    hash --> cmp{"Hash changed?"}
    cmp -->|"no"| skip["Skip"]
    cmp -->|"yes or new"| parse["Parse<br/>text, pages, headings"]
    parse --> redact["Redact PII · P4<br/>optional"]
    redact --> chunk["Chunk"]
    chunk --> embed["Embed in batches"]
    embed --> write["Write in one transaction<br/>replace document and chunks"]
    write --> bump["Bump index version<br/>invalidates caches"]

    classDef optional stroke-dasharray: 5 5
    class redact optional
```

## Sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as CLI or API
    participant Q as Redis queue
    participant W as Worker
    participant I as IngestionService
    participant P as Postgres
    participant D as Dead-letter queue

    U->>Q: enqueue(source_uri) · P4
    Q->>W: job
    W->>I: ingest(source_uri)
    I->>I: read bytes, compute content hash
    I->>P: lookup document by source_uri
    alt hash unchanged
        I-->>W: skipped
    else new or changed
        I->>I: parse, redact PII, chunk, embed
        I->>P: in one transaction, delete old chunks, insert new chunks, update document
        I->>P: bump index version
        I-->>W: indexed
    end
    alt failure after max retries with backoff
        W->>D: move job with error
    end
```

## Consistency rules

| Event | What happens | Guarantee |
| --- | --- | --- |
| New file | Parsed, chunked, embedded, inserted | Document and chunks appear together or not at all |
| Unchanged file | Skipped after the hash check | Re-running ingest on the same corpus does no work |
| Changed file | Old chunks deleted, new chunks inserted, in one transaction | Queries never see a mix of old and new chunks |
| Deleted file (`--prune` or `DELETE /documents`) | Document row deleted, chunks cascade | No stale chunks in any index, because BM25 lives in the same table |
| Embedding model changed | Writes are refused until a full reindex | No index mixes vectors from two models |
| Parse failure | Logged with the file and reason; the run continues | One bad file never blocks the rest; the worker retries, then uses the DLQ |

In the scaled design, where vectors live in Qdrant and BM25 in OpenSearch, a single transaction is no longer possible. There, Postgres keeps an outbox table of index changes and a relay applies them to both indexes idempotently. See [11 · Deployment](11-deployment.md).

## Chunking

| Strategy | Splits on | Phase |
| --- | --- | --- |
| Fixed | Token windows with overlap | P1 |
| Recursive | Headings, then paragraphs, then sentences, until under the size limit | P1 |
| Structure-aware | Contract sections and clause numbers (`12.1`, `ARTICLE IV`) | P3 |
| Semantic | Embedding-similarity breakpoints between sentences | P3 |

Token counts use the embedder's own tokenizer, so a chunk never gets silently truncated at embedding time. The chunking study in P3 compares all four on the eval set.

### Parent/child chunks (P3)

Retrieval runs on small child chunks for precision. The context builder then swaps each hit for its parent, so the LLM sees the whole clause or section.

```mermaid
flowchart TB
    doc["Document<br/>Master Services Agreement"] --> s1["Parent chunk<br/>Section 12 · Governing Law"]
    doc --> s2["Parent chunk<br/>Section 13 · Termination"]
    s1 --> c1["Child chunk<br/>12.1 laws of Delaware"]
    s1 --> c2["Child chunk<br/>12.2 venue and jurisdiction"]
    s2 --> c3["Child chunk<br/>13.1 termination for cause"]
```

## Configuration

```yaml
ingestion:
  parsers: [pdf, docx, html, markdown]
  pii_redaction: false            # P4
chunker: {name: recursive, size_tokens: 400, overlap_tokens: 50}
embedder: {name: fastembed, model: BAAI/bge-small-en-v1.5, batch_size: 64}
```
