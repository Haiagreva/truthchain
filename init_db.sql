-- init_db.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS official_statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    source_url TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE official_statements DISABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS official_statements_embedding_idx 
ON official_statements USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE OR REPLACE FUNCTION match_statements (
  query_embedding VECTOR(384),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  source_url TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    official_statements.id,
    official_statements.content,
    official_statements.source_url,
    1 - (official_statements.embedding <=> query_embedding) AS similarity
  FROM official_statements
  WHERE 1 - (official_statements.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

DROP TABLE IF EXISTS votes;
DROP TABLE IF EXISTS claims;
DROP TABLE IF EXISTS nodes;

CREATE TABLE nodes (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    handle TEXT NOT NULL,
    color TEXT NOT NULL,
    strike_count INT DEFAULT 0,
    is_banned BOOLEAN DEFAULT false,
    banned_until TIMESTAMP WITH TIME ZONE
);

INSERT INTO nodes (id, name, handle, color) VALUES
('00000000-0000-0000-0000-000000000001', 'Haiagreva', 'node_alpha', 'from-blue-500 to-twitter'),
('00000000-0000-0000-0000-000000000002', 'Parth', 'node_beta', 'from-emerald-500 to-green-400'),
('00000000-0000-0000-0000-000000000003', 'Vivek', 'observer_01', 'from-purple-500 to-pink-500'),
('00000000-0000-0000-0000-000000000004', 'Maya', 'validator_x', 'from-rose-500 to-red-400'),
('00000000-0000-0000-0000-000000000005', 'jonhy nikhil', 'oracle_prime', 'from-amber-500 to-yellow-400'),
('00000000-0000-0000-0000-000000000006', 'Saurav jha', 'satoshin', 'from-indigo-500 to-blue-400'),
('00000000-0000-0000-0000-000000000007', 'rupali', 'veritas_node', 'from-teal-500 to-emerald-400'),
('00000000-0000-0000-0000-000000000008', 'chetana', 'echo_system', 'from-fuchsia-500 to-purple-400');

CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID REFERENCES nodes(id) NOT NULL,
    claim_text TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    blockchain_tx_id TEXT,
    blockchain_explorer_url TEXT,
    analysis TEXT,
    confidence_score FLOAT,
    is_flagged BOOLEAN DEFAULT false,
    ai_correction_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID REFERENCES claims(id) ON DELETE CASCADE NOT NULL,
    node_id UUID REFERENCES nodes(id) NOT NULL,
    vote TEXT CHECK (vote IN ('verify', 'refute')) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(claim_id, node_id)
);

ALTER TABLE nodes DISABLE ROW LEVEL SECURITY;
ALTER TABLE claims DISABLE ROW LEVEL SECURITY;
ALTER TABLE votes DISABLE ROW LEVEL SECURITY;
