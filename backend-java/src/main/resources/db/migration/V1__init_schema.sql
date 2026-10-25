CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
                       id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                       email         VARCHAR(255) NOT NULL UNIQUE,
                       password_hash VARCHAR(255) NOT NULL,
                       role          VARCHAR(20)  NOT NULL DEFAULT 'USER',
                       created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE data_sources (
                              id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                              owner_id      UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                              name          VARCHAR(255) NOT NULL,
                              type          VARCHAR(10)  NOT NULL CHECK (type IN ('PDF','TXT','CSV')),
                              status        VARCHAR(20)  NOT NULL DEFAULT 'UPLOADED',
                              storage_key   VARCHAR(500) NOT NULL,
                              size_bytes    BIGINT       NOT NULL,
                              checksum      VARCHAR(64)  NOT NULL,
                              error_message TEXT,
                              created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
                              CONSTRAINT uq_source_owner_checksum UNIQUE (owner_id, checksum)
);
CREATE INDEX idx_sources_owner ON data_sources(owner_id);

CREATE TABLE documents (
                           id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                           source_id  UUID         NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
                           title      VARCHAR(255),
                           checksum   VARCHAR(64),
                           page_count INT,
                           metadata   JSONB        NOT NULL DEFAULT '{}'::jsonb,
                           created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_documents_source ON documents(source_id);

CREATE TABLE document_chunks (
                                 id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                                 document_id     UUID         NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                                 chunk_index     INT          NOT NULL,
                                 content         TEXT         NOT NULL,
                                 page_number     INT,
                                 embedding       vector(384),
                                 embedding_model VARCHAR(100),
                                 tsv             tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
                                 created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
                                 CONSTRAINT uq_chunk_doc_idx UNIQUE (document_id, chunk_index)
);
CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_tsv ON document_chunks USING GIN (tsv);
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE TABLE investigations (
                                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                                user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                question   TEXT        NOT NULL,
                                status     VARCHAR(20) NOT NULL DEFAULT 'QUEUED',
                                answer     JSONB,
                                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_investigations_user ON investigations(user_id, created_at DESC);

CREATE TABLE investigation_sources (
                                       investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
                                       source_id        UUID NOT NULL REFERENCES data_sources(id)   ON DELETE CASCADE,
                                       PRIMARY KEY (investigation_id, source_id)
);

CREATE TABLE investigation_runs (
                                    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                                    investigation_id UUID        NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
                                    run_number       INT         NOT NULL,
                                    status           VARCHAR(20) NOT NULL,
                                    latency_ms       INT,
                                    stage_timings    JSONB,
                                    error_code       VARCHAR(50),
                                    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                                    finished_at      TIMESTAMPTZ,
                                    CONSTRAINT uq_run_number UNIQUE (investigation_id, run_number)
);

CREATE TABLE retrieved_evidence (
                                    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                                    run_id           UUID             NOT NULL REFERENCES investigation_runs(id) ON DELETE CASCADE,
                                    chunk_id         UUID             NOT NULL REFERENCES document_chunks(id)    ON DELETE CASCADE,
                                    score            DOUBLE PRECISION,
                                    rank             INT              NOT NULL,
                                    retrieval_method VARCHAR(20)
);
CREATE INDEX idx_evidence_run ON retrieved_evidence(run_id);

CREATE TABLE citations (
                           id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                           run_id         UUID NOT NULL REFERENCES investigation_runs(id) ON DELETE CASCADE,
                           chunk_id       UUID NOT NULL REFERENCES document_chunks(id)    ON DELETE CASCADE,
                           answer_section TEXT
);
CREATE INDEX idx_citations_run ON citations(run_id);

CREATE TABLE audit_events (
                              id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                              actor_id      UUID,
                              action        VARCHAR(50) NOT NULL,
                              resource_type VARCHAR(50),
                              resource_id   UUID,
                              request_id    VARCHAR(64),
                              created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_actor ON audit_events(actor_id, created_at DESC);