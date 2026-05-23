-- Runs automatically on first Postgres container start (mounted into
-- /docker-entrypoint-initdb.d). Enables pgvector now so Phase 2 RAG needs no migration.
CREATE EXTENSION IF NOT EXISTS vector;
