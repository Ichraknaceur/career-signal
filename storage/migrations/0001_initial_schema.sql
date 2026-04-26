PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    workflow_type TEXT NOT NULL,
    status TEXT NOT NULL,
    trigger_mode TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    input_payload TEXT,
    output_payload TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS workflow_events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata_json TEXT,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS content_drafts (
    id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    source_type TEXT,
    source_ref TEXT,
    title TEXT,
    body TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'French',
    status TEXT NOT NULL,
    qa_score REAL,
    qa_feedback TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scheduled_posts (
    id TEXT PRIMARY KEY,
    draft_id TEXT,
    platform TEXT NOT NULL DEFAULT 'linkedin',
    pillar TEXT,
    scheduled_for TEXT NOT NULL,
    approved_at TEXT,
    published_at TEXT,
    status TEXT NOT NULL,
    content TEXT NOT NULL,
    hashtags_json TEXT,
    medium_article_url TEXT,
    medium_article_title TEXT,
    run_id TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (draft_id) REFERENCES content_drafts(id) ON DELETE SET NULL,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status_date
ON scheduled_posts(status, scheduled_for);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    linkedin_url TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    first_name TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    summary TEXT,
    contact_type TEXT NOT NULL DEFAULT 'peer',
    source TEXT NOT NULL DEFAULT 'linkedin',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_messages (
    id TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL,
    campaign_id TEXT,
    message_type TEXT NOT NULL DEFAULT 'connection_request',
    language TEXT NOT NULL DEFAULT 'French',
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    sent_at TEXT,
    replied_at TEXT,
    last_checked_at TEXT,
    user_feedback TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_outreach_messages_status
ON outreach_messages(status);

CREATE TABLE IF NOT EXISTS job_postings (
    id TEXT PRIMARY KEY,
    external_id TEXT,
    source TEXT NOT NULL DEFAULT 'linkedin_jobs',
    source_url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    employment_type TEXT,
    posted_at TEXT,
    discovered_at TEXT NOT NULL,
    keywords_json TEXT,
    description TEXT,
    recruiter_contact_id TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    notes TEXT,
    FOREIGN KEY (recruiter_contact_id) REFERENCES contacts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_job_postings_status_discovered
ON job_postings(status, discovered_at);

CREATE TABLE IF NOT EXISTS watch_topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    keywords_json TEXT NOT NULL,
    source_scope TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watch_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    category TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    last_checked_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watch_articles (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    topic_id TEXT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    suggested_post TEXT,
    published_at TEXT,
    discovered_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    FOREIGN KEY (source_id) REFERENCES watch_sources(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES watch_topics(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_watch_articles_status_discovered
ON watch_articles(status, discovered_at);
