-- Create knowledge_base_prompts table for SQLite
-- This script creates the new table needed for prompt individuation

CREATE TABLE IF NOT EXISTS knowledge_base_prompts (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
    collection_name TEXT NOT NULL UNIQUE,
    certification_name TEXT NOT NULL,

    -- Knowledge base operation prompts
    document_ingestion_prompt TEXT,
    context_retrieval_prompt TEXT,
    semantic_search_prompt TEXT,
    content_classification_prompt TEXT,

    -- Metadata
    version TEXT NOT NULL DEFAULT 'v1.0',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create index on collection_name for faster lookups
CREATE INDEX IF NOT EXISTS idx_knowledge_base_prompts_collection_name
ON knowledge_base_prompts(collection_name);

-- Create index on certification_name for filtering
CREATE INDEX IF NOT EXISTS idx_knowledge_base_prompts_certification_name
ON knowledge_base_prompts(certification_name);

-- Create trigger to automatically update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_knowledge_base_prompts_updated_at
    AFTER UPDATE ON knowledge_base_prompts
    FOR EACH ROW
BEGIN
    UPDATE knowledge_base_prompts
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;