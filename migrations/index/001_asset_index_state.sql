CREATE TABLE asset_index_state (
    asset_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    representation_version TEXT NOT NULL,
    embedding_model_id TEXT NOT NULL,
    embedding_model_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    skill_row_id INTEGER NOT NULL,
    vector_row_id INTEGER NOT NULL,
    source_path TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    PRIMARY KEY (
        asset_id,
        revision_id,
        representation_version,
        embedding_model_id,
        embedding_model_version
    ),
    UNIQUE (skill_row_id),
    UNIQUE (vector_row_id),
    FOREIGN KEY (skill_row_id) REFERENCES skills(id) ON DELETE CASCADE
);

CREATE INDEX idx_asset_index_state_source_path
ON asset_index_state(source_path);
