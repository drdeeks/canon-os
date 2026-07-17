-- Canon OS initial PostgreSQL schema.
-- Blueprint reference: Part IV, section 4.1 ([DATA-ARCH-v1]).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Users and Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('admin', 'manager', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Brand Identities
CREATE TABLE brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    logo_url VARCHAR(500),
    primary_color VARCHAR(7) NOT NULL,
    secondary_color VARCHAR(7),
    tone VARCHAR(50) CHECK (tone IN ('professional', 'casual', 'playful', 'luxury', 'minimalist')),
    target_audience TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_brands_user_id ON brands(user_id);

-- Campaigns
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'active', 'paused', 'completed')),
    posting_frequency VARCHAR(50) CHECK (posting_frequency IN ('daily', '3x_week', '2x_week', 'weekly')),
    platforms TEXT[] NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    duration_days INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX idx_campaigns_brand_id ON campaigns(brand_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- Content Assets (videos, images, audio)
CREATE TABLE content_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL CHECK (asset_type IN ('video', 'image', 'audio', 'text')),
    title VARCHAR(255),
    description TEXT,
    file_url VARCHAR(500) NOT NULL,
    file_size_mb FLOAT,
    duration_seconds INTEGER,
    resolution VARCHAR(20),
    format VARCHAR(50),
    checksum VARCHAR(64) NOT NULL,
    backend_used VARCHAR(20) DEFAULT 'local',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_assets_campaign_id ON content_assets(campaign_id);
CREATE INDEX idx_content_assets_brand_id ON content_assets(brand_id);
CREATE INDEX idx_content_assets_type ON content_assets(asset_type);

-- Scheduled Posts
CREATE TABLE scheduled_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    content_asset_id UUID NOT NULL REFERENCES content_assets(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('instagram', 'tiktok', 'youtube', 'linkedin', 'twitter', 'facebook')),
    caption TEXT,
    hashtags TEXT[],
    scheduled_at TIMESTAMPTZ NOT NULL,
    posted_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'posted', 'failed', 'cancelled')),
    post_url VARCHAR(500),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scheduled_posts_campaign_id ON scheduled_posts(campaign_id);
CREATE INDEX idx_scheduled_posts_platform ON scheduled_posts(platform);
CREATE INDEX idx_scheduled_posts_status ON scheduled_posts(status);
CREATE INDEX idx_scheduled_posts_scheduled_at ON scheduled_posts(scheduled_at);

-- Analytics Metrics
CREATE TABLE analytics_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheduled_post_id UUID NOT NULL REFERENCES scheduled_posts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    engagement_rate FLOAT,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_metrics_post_id ON analytics_metrics(scheduled_post_id);
CREATE INDEX idx_analytics_metrics_platform ON analytics_metrics(platform);
CREATE INDEX idx_analytics_metrics_collected_at ON analytics_metrics(collected_at);

-- Social Platform Auth (OAuth tokens)
CREATE TABLE social_auth (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL CHECK (platform IN ('instagram', 'tiktok', 'youtube', 'linkedin', 'twitter', 'facebook')),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    account_id VARCHAR(255),
    account_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, platform)
);

CREATE INDEX idx_social_auth_user_id ON social_auth(user_id);
CREATE INDEX idx_social_auth_platform ON social_auth(platform);

-- Provider Keys (backend registry, by reference only)
CREATE TABLE provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    modality VARCHAR(20) NOT NULL CHECK (modality IN ('image', 'video', 'audio', 'text', 'stt', 'music')),
    provider VARCHAR(50) NOT NULL,
    key_ref VARCHAR(500) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, modality, provider)
);

CREATE INDEX idx_provider_keys_user_id ON provider_keys(user_id);

-- Job Queue (RabbitMQ metadata)
CREATE TABLE job_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_job_queue_status ON job_queue(status);
CREATE INDEX idx_job_queue_priority ON job_queue(priority DESC);
CREATE INDEX idx_job_queue_created_at ON job_queue(created_at);

-- Agent Logs (every create/verify agent output, by phase)
CREATE TABLE agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phase_index INTEGER NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    role VARCHAR(32) NOT NULL,
    action VARCHAR(32) NOT NULL CHECK (action IN ('create', 'verify', 'revise')),
    artifact_path TEXT,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_logs_phase ON agent_logs(phase_index);
CREATE INDEX idx_agent_logs_agent ON agent_logs(agent_id);

-- Audit Trail (append-only, never purged)
CREATE TABLE audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor VARCHAR(64) NOT NULL,
    action VARCHAR(128) NOT NULL,
    target VARCHAR(256),
    detail JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_trail_created ON audit_trail(created_at);

-- Backups & Archives
CREATE TABLE backups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind VARCHAR(32) NOT NULL CHECK (kind IN ('daily', 'weekly', 'archive')),
    location VARCHAR(500) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Policy / Compliance Rules
CREATE TABLE policy_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction VARCHAR(32) NOT NULL,
    rule_type VARCHAR(64) NOT NULL,
    constraint_json JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_policy_rules_jurisdiction ON policy_rules(jurisdiction);
