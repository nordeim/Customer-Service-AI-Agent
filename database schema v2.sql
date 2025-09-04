-- =====================================================================================
-- AI CUSTOMER SERVICE AGENT - POSTGRESQL v16 DATABASE SCHEMA
-- Version: 2.0.0
-- Description: Production-ready database schema for AI-powered customer service agent
-- PostgreSQL Version: 16.x
-- =====================================================================================

-- =====================================================================================
-- INITIAL SETUP & EXTENSIONS
-- =====================================================================================

-- Create database (run as superuser)
-- CREATE DATABASE ai_customer_service_agent
--     WITH 
--     OWNER = ai_agent_admin
--     ENCODING = 'UTF8'
--     LC_COLLATE = 'en_US.UTF-8'
--     LC_CTYPE = 'en_US.UTF-8'
--     TABLESPACE = pg_default
--     CONNECTION LIMIT = -1;

-- Connect to the database
\c ai_customer_service_agent;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";        -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";         -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";          -- Trigram text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";        -- GIN index support for btree
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query performance monitoring
CREATE EXTENSION IF NOT EXISTS "postgres_fdw";     -- Foreign data wrapper
CREATE EXTENSION IF NOT EXISTS "hstore";           -- Key-value store
CREATE EXTENSION IF NOT EXISTS "pg_cron";          -- Job scheduling
CREATE EXTENSION IF NOT EXISTS "vector";           -- Vector similarity search (pgvector)

-- =====================================================================================
-- SCHEMAS
-- =====================================================================================

-- Core schema for main application tables
CREATE SCHEMA IF NOT EXISTS core;

-- Analytics schema for reporting and metrics
CREATE SCHEMA IF NOT EXISTS analytics;

-- Audit schema for audit trails and compliance
CREATE SCHEMA IF NOT EXISTS audit;

-- AI schema for machine learning related data
CREATE SCHEMA IF NOT EXISTS ai;

-- Cache schema for cached computations
CREATE SCHEMA IF NOT EXISTS cache;

-- Set default search path
SET search_path TO core, public;

-- =====================================================================================
-- CUSTOM TYPES AND DOMAINS
-- =====================================================================================

-- Enum types for better data integrity
CREATE TYPE core.conversation_status AS ENUM (
    'active',
    'waiting_for_user',
    'waiting_for_agent',
    'escalated',
    'resolved',
    'abandoned',
    'archived'
);

CREATE TYPE core.message_sender_type AS ENUM (
    'user',
    'ai_agent',
    'human_agent',
    'system'
);

CREATE TYPE core.channel_type AS ENUM (
    'web',
    'mobile_ios',
    'mobile_android',
    'email',
    'slack',
    'teams',
    'whatsapp',
    'sms',
    'api',
    'widget'
);

CREATE TYPE core.priority_level AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

CREATE TYPE core.sentiment AS ENUM (
    'very_negative',
    'negative',
    'neutral',
    'positive',
    'very_positive'
);

CREATE TYPE core.subscription_tier AS ENUM (
    'free',
    'starter',
    'professional',
    'enterprise',
    'custom'
);

CREATE TYPE core.action_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'cancelled',
    'timeout'
);

CREATE TYPE core.escalation_reason AS ENUM (
    'user_requested',
    'sentiment_negative',
    'low_confidence',
    'complex_issue',
    'repeated_attempts',
    'vip_customer',
    'compliance_required',
    'technical_error'
);

-- Custom domains for validation
CREATE DOMAIN core.email AS TEXT
    CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

CREATE DOMAIN core.url AS TEXT
    CHECK (VALUE ~* '^https?://[A-Za-z0-9.-]+(\.[A-Za-z]{2,})+');

CREATE DOMAIN core.positive_integer AS INTEGER
    CHECK (VALUE > 0);

CREATE DOMAIN core.percentage AS DECIMAL(5,2)
    CHECK (VALUE >= 0 AND VALUE <= 100);

-- =====================================================================================
-- CORE SCHEMA TABLES
-- =====================================================================================

-- -----------------------------------------------------------------------------
-- Organizations table (multi-tenancy root)
-- -----------------------------------------------------------------------------
CREATE TABLE core.organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    
    -- Salesforce integration
    salesforce_org_id VARCHAR(18) UNIQUE,
    salesforce_instance_url core.url,
    
    -- Subscription and limits
    subscription_tier core.subscription_tier NOT NULL DEFAULT 'starter',
    subscription_expires_at TIMESTAMPTZ,
    max_users INTEGER DEFAULT 10,
    max_conversations_per_month INTEGER DEFAULT 1000,
    max_api_calls_per_day INTEGER DEFAULT 10000,
    
    -- Settings and configuration
    settings JSONB NOT NULL DEFAULT '{}',
    features JSONB NOT NULL DEFAULT '{"ai_enabled": true, "escalation_enabled": true}',
    custom_branding JSONB DEFAULT '{}',
    
    -- Timezone and locale
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en_US',
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    trial_ends_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT chk_org_max_users CHECK (max_users >= 0),
    CONSTRAINT chk_org_max_conversations CHECK (max_conversations_per_month >= 0),
    CONSTRAINT chk_org_trial_date CHECK (trial_ends_at IS NULL OR trial_ends_at > created_at)
);

-- Indexes for organizations
CREATE INDEX idx_organizations_salesforce_org_id ON core.organizations(salesforce_org_id) WHERE salesforce_org_id IS NOT NULL;
CREATE INDEX idx_organizations_subscription_tier ON core.organizations(subscription_tier);
CREATE INDEX idx_organizations_is_active ON core.organizations(is_active) WHERE is_active = true;
CREATE INDEX idx_organizations_created_at ON core.organizations(created_at DESC);
CREATE INDEX idx_organizations_settings_gin ON core.organizations USING gin(settings);
CREATE INDEX idx_organizations_tags_gin ON core.organizations USING gin(tags);

-- -----------------------------------------------------------------------------
-- Users table
-- -----------------------------------------------------------------------------
CREATE TABLE core.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    
    -- Authentication
    email core.email NOT NULL,
    email_verified BOOLEAN DEFAULT false,
    password_hash VARCHAR(255),
    mfa_enabled BOOLEAN DEFAULT false,
    mfa_secret VARCHAR(255),
    
    -- Profile
    username VARCHAR(100) UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(200),
    avatar_url core.url,
    phone_number VARCHAR(20),
    
    -- Salesforce integration
    salesforce_user_id VARCHAR(18),
    salesforce_contact_id VARCHAR(18),
    
    -- Role and permissions
    role VARCHAR(50) DEFAULT 'customer',
    permissions JSONB DEFAULT '{}',
    
    -- Customer attributes
    customer_tier VARCHAR(50),
    customer_since DATE,
    lifetime_value DECIMAL(15,2),
    
    -- Preferences
    preferred_language VARCHAR(10) DEFAULT 'en',
    preferred_channel core.channel_type,
    notification_preferences JSONB DEFAULT '{"email": true, "sms": false, "push": true}',
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_online BOOLEAN DEFAULT false,
    last_seen_at TIMESTAMPTZ,
    
    -- Rate limiting
    api_key VARCHAR(255) UNIQUE,
    api_rate_limit INTEGER DEFAULT 1000,
    
    -- Metadata
    attributes JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT chk_users_lifetime_value CHECK (lifetime_value >= 0),
    CONSTRAINT uq_users_org_email UNIQUE (organization_id, email),
    CONSTRAINT uq_users_org_external_id UNIQUE (organization_id, external_id)
);

-- Indexes for users
CREATE INDEX idx_users_organization_id ON core.users(organization_id);
CREATE INDEX idx_users_email ON core.users(email);
CREATE INDEX idx_users_username ON core.users(username) WHERE username IS NOT NULL;
CREATE INDEX idx_users_salesforce_ids ON core.users(salesforce_user_id, salesforce_contact_id) 
    WHERE salesforce_user_id IS NOT NULL OR salesforce_contact_id IS NOT NULL;
CREATE INDEX idx_users_is_active ON core.users(organization_id, is_active) WHERE is_active = true;
CREATE INDEX idx_users_customer_tier ON core.users(customer_tier) WHERE customer_tier IS NOT NULL;
CREATE INDEX idx_users_created_at ON core.users(created_at DESC);
CREATE INDEX idx_users_last_seen_at ON core.users(last_seen_at DESC) WHERE last_seen_at IS NOT NULL;
CREATE INDEX idx_users_tags_gin ON core.users USING gin(tags);
CREATE INDEX idx_users_attributes_gin ON core.users USING gin(attributes);

-- -----------------------------------------------------------------------------
-- Conversations table
-- -----------------------------------------------------------------------------
CREATE TABLE core.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    
    -- Conversation details
    title VARCHAR(500),
    channel core.channel_type NOT NULL,
    status core.conversation_status NOT NULL DEFAULT 'active',
    priority core.priority_level DEFAULT 'medium',
    
    -- Assignment
    assigned_agent_id UUID REFERENCES core.users(id),
    assigned_at TIMESTAMPTZ,
    queue_name VARCHAR(100),
    
    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    first_response_at TIMESTAMPTZ,
    
    -- Metrics
    message_count INTEGER DEFAULT 0,
    user_message_count INTEGER DEFAULT 0,
    agent_message_count INTEGER DEFAULT 0,
    
    -- AI metrics
    ai_handled BOOLEAN DEFAULT true,
    ai_confidence_avg core.percentage,
    ai_resolution_score core.percentage,
    
    -- Sentiment tracking
    sentiment_current core.sentiment DEFAULT 'neutral',
    sentiment_trend VARCHAR(20), -- improving, declining, stable
    sentiment_scores JSONB DEFAULT '[]', -- Array of {timestamp, score}
    
    -- Resolution
    resolved_by VARCHAR(50), -- ai_agent, human_agent, user, system
    resolution_time_seconds INTEGER,
    resolution_summary TEXT,
    
    -- Escalation
    escalated BOOLEAN DEFAULT false,
    escalation_reason core.escalation_reason,
    escalated_at TIMESTAMPTZ,
    
    -- Customer satisfaction
    satisfaction_score DECIMAL(2,1) CHECK (satisfaction_score >= 1 AND satisfaction_score <= 5),
    satisfaction_feedback TEXT,
    feedback_submitted_at TIMESTAMPTZ,
    
    -- Context and state
    context JSONB NOT NULL DEFAULT '{}',
    session_data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Language
    language VARCHAR(10) DEFAULT 'en',
    
    -- Related data
    salesforce_case_id VARCHAR(18),
    salesforce_case_number VARCHAR(50),
    parent_conversation_id UUID REFERENCES core.conversations(id),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_conv_ended_after_started CHECK (ended_at IS NULL OR ended_at >= started_at),
    CONSTRAINT chk_conv_resolution_time CHECK (resolution_time_seconds >= 0),
    CONSTRAINT chk_conv_message_counts CHECK (
        message_count >= 0 AND 
        user_message_count >= 0 AND 
        agent_message_count >= 0
    )
);

-- Indexes for conversations
CREATE INDEX idx_conversations_organization_id ON core.conversations(organization_id);
CREATE INDEX idx_conversations_user_id ON core.conversations(user_id);
CREATE INDEX idx_conversations_status ON core.conversations(status);
CREATE INDEX idx_conversations_channel_status ON core.conversations(channel, status);
CREATE INDEX idx_conversations_priority ON core.conversations(priority) WHERE priority IN ('high', 'critical');
CREATE INDEX idx_conversations_assigned_agent ON core.conversations(assigned_agent_id) WHERE assigned_agent_id IS NOT NULL;
CREATE INDEX idx_conversations_started_at ON core.conversations(started_at DESC);
CREATE INDEX idx_conversations_last_activity ON core.conversations(last_activity_at DESC);
CREATE INDEX idx_conversations_escalated ON core.conversations(escalated, escalated_at) WHERE escalated = true;
CREATE INDEX idx_conversations_salesforce_case ON core.conversations(salesforce_case_id) WHERE salesforce_case_id IS NOT NULL;
CREATE INDEX idx_conversations_parent ON core.conversations(parent_conversation_id) WHERE parent_conversation_id IS NOT NULL;
CREATE INDEX idx_conversations_active ON core.conversations(organization_id, status, last_activity_at DESC) 
    WHERE status IN ('active', 'waiting_for_user', 'waiting_for_agent');
CREATE INDEX idx_conversations_context_gin ON core.conversations USING gin(context);
CREATE INDEX idx_conversations_tags_gin ON core.conversations USING gin(tags);

-- -----------------------------------------------------------------------------
-- Messages table (partitioned by created_at)
-- -----------------------------------------------------------------------------
CREATE TABLE core.messages (
    id UUID DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    
    -- Message details
    sender_type core.message_sender_type NOT NULL,
    sender_id UUID,
    sender_name VARCHAR(255),
    
    -- Content
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text', -- text, html, markdown, code, etc.
    content_translated TEXT,
    original_language VARCHAR(10),
    
    -- AI processing results
    intent VARCHAR(100),
    intent_confidence core.percentage,
    entities JSONB DEFAULT '[]',
    sentiment_score DECIMAL(3,2), -- -1 to 1
    sentiment_label core.sentiment,
    
    -- Moderation
    is_flagged BOOLEAN DEFAULT false,
    flagged_reason VARCHAR(255),
    moderation_score JSONB,
    
    -- Attachments
    attachments JSONB DEFAULT '[]',
    attachment_count INTEGER DEFAULT 0,
    
    -- Message state
    is_internal BOOLEAN DEFAULT false,
    is_automated BOOLEAN DEFAULT false,
    is_edited BOOLEAN DEFAULT false,
    edited_at TIMESTAMPTZ,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMPTZ,
    
    -- Read receipts
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    
    -- Related messages
    in_reply_to UUID,
    thread_id UUID,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    processing_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Primary key includes created_at for partitioning
    PRIMARY KEY (id, created_at),
    
    -- Foreign keys
    FOREIGN KEY (conversation_id) REFERENCES core.conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES core.organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES core.users(id) ON DELETE SET NULL,
    
    -- Constraints
    CONSTRAINT chk_messages_sentiment CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    CONSTRAINT chk_messages_attachment_count CHECK (attachment_count >= 0)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for messages
CREATE TABLE core.messages_2024_01 PARTITION OF core.messages
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE core.messages_2024_02 PARTITION OF core.messages
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE core.messages_2024_03 PARTITION OF core.messages
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
-- Add more partitions as needed

-- Indexes for messages (will be created on each partition)
CREATE INDEX idx_messages_conversation_id ON core.messages(conversation_id);
CREATE INDEX idx_messages_organization_id ON core.messages(organization_id);
CREATE INDEX idx_messages_sender ON core.messages(sender_type, sender_id);
CREATE INDEX idx_messages_created_at ON core.messages(created_at DESC);
CREATE INDEX idx_messages_intent ON core.messages(intent) WHERE intent IS NOT NULL;
CREATE INDEX idx_messages_sentiment ON core.messages(sentiment_label) WHERE sentiment_label IS NOT NULL;
CREATE INDEX idx_messages_is_flagged ON core.messages(is_flagged) WHERE is_flagged = true;
CREATE INDEX idx_messages_thread ON core.messages(thread_id) WHERE thread_id IS NOT NULL;
CREATE INDEX idx_messages_entities_gin ON core.messages USING gin(entities);
CREATE INDEX idx_messages_content_search ON core.messages USING gin(to_tsvector('english', content));

-- -----------------------------------------------------------------------------
-- Actions table (for tracking automated actions and tasks)
-- -----------------------------------------------------------------------------
CREATE TABLE core.actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES core.conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES core.users(id) ON DELETE SET NULL,
    
    -- Action details
    action_type VARCHAR(100) NOT NULL, -- password_reset, create_ticket, send_email, etc.
    action_category VARCHAR(50), -- authentication, notification, integration, etc.
    status core.action_status NOT NULL DEFAULT 'pending',
    priority core.priority_level DEFAULT 'medium',
    
    -- Execution details
    parameters JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    error_message TEXT,
    error_details JSONB,
    
    -- Timing
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- Retry logic
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    retry_after TIMESTAMPTZ,
    
    -- Dependencies
    depends_on UUID[], -- Array of action IDs this depends on
    blocks UUID[], -- Array of action IDs this blocks
    
    -- Audit
    initiated_by VARCHAR(50), -- user, ai_agent, system, workflow
    approved_by UUID REFERENCES core.users(id),
    approved_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_actions_retry_count CHECK (retry_count >= 0),
    CONSTRAINT chk_actions_max_retries CHECK (max_retries >= 0),
    CONSTRAINT chk_actions_duration CHECK (duration_ms >= 0)
);

-- Indexes for actions
CREATE INDEX idx_actions_organization_id ON core.actions(organization_id);
CREATE INDEX idx_actions_conversation_id ON core.actions(conversation_id) WHERE conversation_id IS NOT NULL;
CREATE INDEX idx_actions_user_id ON core.actions(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_actions_status ON core.actions(status);
CREATE INDEX idx_actions_type_status ON core.actions(action_type, status);
CREATE INDEX idx_actions_scheduled ON core.actions(scheduled_at) WHERE scheduled_at IS NOT NULL AND status = 'pending';
CREATE INDEX idx_actions_retry ON core.actions(retry_after) WHERE retry_after IS NOT NULL AND status = 'failed';
CREATE INDEX idx_actions_created_at ON core.actions(created_at DESC);
CREATE INDEX idx_actions_depends_on_gin ON core.actions USING gin(depends_on);
CREATE INDEX idx_actions_tags_gin ON core.actions USING gin(tags);

-- -----------------------------------------------------------------------------
-- Escalations table
-- -----------------------------------------------------------------------------
CREATE TABLE core.escalations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES core.conversations(id) ON DELETE CASCADE,
    
    -- Escalation details
    reason core.escalation_reason NOT NULL,
    reason_details TEXT,
    priority core.priority_level NOT NULL DEFAULT 'high',
    
    -- Assignment
    assigned_to UUID REFERENCES core.users(id),
    assigned_at TIMESTAMPTZ,
    assignment_method VARCHAR(50), -- manual, round_robin, skills_based, workload
    queue_name VARCHAR(100),
    team_name VARCHAR(100),
    
    -- SLA tracking
    sla_name VARCHAR(100),
    sla_deadline TIMESTAMPTZ,
    sla_breached BOOLEAN DEFAULT false,
    response_time_seconds INTEGER,
    resolution_time_seconds INTEGER,
    
    -- Resolution
    status VARCHAR(50) DEFAULT 'open', -- open, in_progress, resolved, cancelled
    resolved_by UUID REFERENCES core.users(id),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    
    -- Customer communication
    customer_notified BOOLEAN DEFAULT false,
    customer_notified_at TIMESTAMPTZ,
    
    -- Metadata
    context JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_escalations_sla_breach CHECK (
        (sla_breached = false) OR 
        (sla_breached = true AND sla_deadline IS NOT NULL)
    ),
    CONSTRAINT chk_escalations_response_time CHECK (response_time_seconds >= 0),
    CONSTRAINT chk_escalations_resolution_time CHECK (resolution_time_seconds >= 0)
);

-- Indexes for escalations
CREATE INDEX idx_escalations_organization_id ON core.escalations(organization_id);
CREATE INDEX idx_escalations_conversation_id ON core.escalations(conversation_id);
CREATE INDEX idx_escalations_assigned_to ON core.escalations(assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_escalations_status ON core.escalations(status);
CREATE INDEX idx_escalations_priority_status ON core.escalations(priority, status);
CREATE INDEX idx_escalations_sla_deadline ON core.escalations(sla_deadline) WHERE sla_deadline IS NOT NULL;
CREATE INDEX idx_escalations_sla_breached ON core.escalations(sla_breached) WHERE sla_breached = true;
CREATE INDEX idx_escalations_created_at ON core.escalations(created_at DESC);
CREATE INDEX idx_escalations_queue ON core.escalations(queue_name) WHERE queue_name IS NOT NULL;

-- =====================================================================================
-- AI SCHEMA TABLES
-- =====================================================================================

-- -----------------------------------------------------------------------------
-- Knowledge base entries
-- -----------------------------------------------------------------------------
CREATE TABLE ai.knowledge_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    
    -- Content
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    
    -- Categorization
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    topic VARCHAR(100),
    keywords TEXT[],
    
    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    is_current BOOLEAN DEFAULT true,
    parent_id UUID REFERENCES ai.knowledge_entries(id),
    
    -- Source tracking
    source VARCHAR(255),
    source_url core.url,
    source_document_id VARCHAR(255),
    last_synced_at TIMESTAMPTZ,
    
    -- Quality metrics
    quality_score core.percentage DEFAULT 100,
    confidence_score core.percentage DEFAULT 100,
    accuracy_score core.percentage,
    completeness_score core.percentage,
    
    -- Usage metrics
    usage_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    not_helpful_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    -- Validity
    valid_from TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMPTZ,
    is_archived BOOLEAN DEFAULT false,
    archived_at TIMESTAMPTZ,
    archived_reason TEXT,
    
    -- Search optimization
    search_vector tsvector,
    embedding vector(1536), -- OpenAI embeddings dimension
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Review and approval
    requires_review BOOLEAN DEFAULT false,
    reviewed_by UUID REFERENCES core.users(id),
    reviewed_at TIMESTAMPTZ,
    approved_by UUID REFERENCES core.users(id),
    approved_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_knowledge_version CHECK (version > 0),
    CONSTRAINT chk_knowledge_usage_count CHECK (usage_count >= 0),
    CONSTRAINT chk_knowledge_helpful_counts CHECK (helpful_count >= 0 AND not_helpful_count >= 0)
);

-- Indexes for knowledge entries
CREATE INDEX idx_knowledge_organization_id ON ai.knowledge_entries(organization_id);
CREATE INDEX idx_knowledge_category ON ai.knowledge_entries(category, subcategory);
CREATE INDEX idx_knowledge_is_current ON ai.knowledge_entries(is_current) WHERE is_current = true;
CREATE INDEX idx_knowledge_parent_id ON ai.knowledge_entries(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX idx_knowledge_search_vector ON ai.knowledge_entries USING gin(search_vector);
CREATE INDEX idx_knowledge_embedding ON ai.knowledge_entries USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_knowledge_keywords_gin ON ai.knowledge_entries USING gin(keywords);
CREATE INDEX idx_knowledge_tags_gin ON ai.knowledge_entries USING gin(tags);
CREATE INDEX idx_knowledge_valid_current ON ai.knowledge_entries(organization_id, is_current, valid_from, valid_until) 
    WHERE is_current = true AND is_archived = false;

-- Trigger to update search vector
CREATE OR REPLACE FUNCTION ai.update_knowledge_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.keywords, ' '), '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_knowledge_search_vector
    BEFORE INSERT OR UPDATE OF title, content, summary, keywords
    ON ai.knowledge_entries
    FOR EACH ROW
    EXECUTE FUNCTION ai.update_knowledge_search_vector();

-- -----------------------------------------------------------------------------
-- AI Model Interactions table
-- -----------------------------------------------------------------------------
CREATE TABLE ai.model_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES core.conversations(id) ON DELETE CASCADE,
    message_id UUID,
    
    -- Model details
    model_name VARCHAR(100) NOT NULL, -- gpt-4, claude-3, etc.
    model_version VARCHAR(50),
    model_provider VARCHAR(50), -- openai, anthropic, etc.
    
    -- Request
    request_type VARCHAR(50), -- completion, embedding, classification, etc.
    prompt TEXT,
    system_prompt TEXT,
    parameters JSONB DEFAULT '{}',
    
    -- Response
    response TEXT,
    response_metadata JSONB DEFAULT '{}',
    confidence_score core.percentage,
    
    -- Performance metrics
    tokens_input INTEGER,
    tokens_output INTEGER,
    total_tokens INTEGER,
    latency_ms INTEGER,
    
    -- Cost tracking
    cost_input DECIMAL(10,6),
    cost_output DECIMAL(10,6),
    total_cost DECIMAL(10,6),
    
    -- Error handling
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_model_tokens CHECK (
        tokens_input >= 0 AND 
        tokens_output >= 0 AND 
        total_tokens >= 0
    ),
    CONSTRAINT chk_model_costs CHECK (
        cost_input >= 0 AND 
        cost_output >= 0 AND 
        total_cost >= 0
    ),
    CONSTRAINT chk_model_latency CHECK (latency_ms >= 0)
);

-- Indexes for model interactions
CREATE INDEX idx_model_interactions_organization_id ON ai.model_interactions(organization_id);
CREATE INDEX idx_model_interactions_conversation_id ON ai.model_interactions(conversation_id) WHERE conversation_id IS NOT NULL;
CREATE INDEX idx_model_interactions_model ON ai.model_interactions(model_name, model_provider);
CREATE INDEX idx_model_interactions_created_at ON ai.model_interactions(created_at DESC);
CREATE INDEX idx_model_interactions_success ON ai.model_interactions(success) WHERE success = false;

-- =====================================================================================
-- ANALYTICS SCHEMA TABLES & VIEWS
-- =====================================================================================

-- -----------------------------------------------------------------------------
-- Aggregated conversation metrics (materialized view)
-- -----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW analytics.conversation_metrics AS
SELECT 
    DATE_TRUNC('hour', c.started_at) as hour,
    c.organization_id,
    c.channel,
    c.status,
    COUNT(*) as conversation_count,
    AVG(c.resolution_time_seconds)::INTEGER as avg_resolution_time_seconds,
    AVG(c.message_count)::DECIMAL(10,2) as avg_message_count,
    AVG(c.ai_confidence_avg)::DECIMAL(5,2) as avg_ai_confidence,
    AVG(c.satisfaction_score)::DECIMAL(3,2) as avg_satisfaction_score,
    SUM(CASE WHEN c.escalated THEN 1 ELSE 0 END) as escalation_count,
    SUM(CASE WHEN c.ai_handled THEN 1 ELSE 0 END) as ai_handled_count,
    SUM(CASE WHEN c.resolved_by = 'ai_agent' THEN 1 ELSE 0 END) as ai_resolved_count,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY c.resolution_time_seconds) as median_resolution_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY c.resolution_time_seconds) as p95_resolution_time
FROM core.conversations c
WHERE c.started_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('hour', c.started_at), c.organization_id, c.channel, c.status
WITH DATA;

-- Index for materialized view
CREATE UNIQUE INDEX idx_conversation_metrics_unique 
    ON analytics.conversation_metrics(hour, organization_id, channel, status);
CREATE INDEX idx_conversation_metrics_org_hour 
    ON analytics.conversation_metrics(organization_id, hour DESC);

-- -----------------------------------------------------------------------------
-- Intent patterns analysis table
-- -----------------------------------------------------------------------------
CREATE TABLE analytics.intent_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
    
    -- Pattern details
    intent VARCHAR(100) NOT NULL,
    pattern TEXT NOT NULL,
    pattern_regex TEXT,
    
    -- Metrics
    occurrence_count INTEGER DEFAULT 1,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    success_rate core.percentage,
    
    -- Performance
    avg_confidence core.percentage,
    avg_resolution_time_seconds INTEGER,
    avg_message_count DECIMAL(10,2),
    
    -- Dates
    first_seen TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    sample_messages TEXT[],
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_intent_patterns_counts CHECK (
        occurrence_count > 0 AND 
        success_count >= 0 AND 
        failure_count >= 0
    ),
    CONSTRAINT uq_intent_patterns_org_intent_pattern UNIQUE (organization_id, intent, pattern)
);

-- Indexes for intent patterns
CREATE INDEX idx_intent_patterns_organization_id ON analytics.intent_patterns(organization_id);
CREATE INDEX idx_intent_patterns_intent ON analytics.intent_patterns(intent);
CREATE INDEX idx_intent_patterns_occurrence ON analytics.intent_patterns(occurrence_count DESC);
CREATE INDEX idx_intent_patterns_success_rate ON analytics.intent_patterns(success_rate DESC) WHERE success_rate IS NOT NULL;

-- =====================================================================================
-- AUDIT SCHEMA TABLES
-- =====================================================================================

-- -----------------------------------------------------------------------------
-- Audit log table (partitioned by timestamp)
-- -----------------------------------------------------------------------------
CREATE TABLE audit.activity_log (
    id UUID DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Actor
    organization_id UUID,
    user_id UUID,
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    
    -- Action
    action VARCHAR(100) NOT NULL, -- create, update, delete, view, export, etc.
    resource_type VARCHAR(50) NOT NULL, -- conversation, user, knowledge, etc.
    resource_id UUID,
    resource_name VARCHAR(255),
    
    -- Details
    old_values JSONB,
    new_values JSONB,
    change_summary TEXT,
    
    -- Request context
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(255),
    request_id VARCHAR(255),
    
    -- Response
    status_code INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Primary key includes timestamp for partitioning
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions for audit log
CREATE TABLE audit.activity_log_2024_01 PARTITION OF audit.activity_log
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE audit.activity_log_2024_02 PARTITION OF audit.activity_log
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE audit.activity_log_2024_03 PARTITION OF audit.activity_log
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
-- Add more partitions as needed

-- Indexes for audit log
CREATE INDEX idx_activity_log_timestamp ON audit.activity_log(timestamp DESC);
CREATE INDEX idx_activity_log_organization_id ON audit.activity_log(organization_id) WHERE organization_id IS NOT NULL;
CREATE INDEX idx_activity_log_user_id ON audit.activity_log(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_activity_log_action ON audit.activity_log(action);
CREATE INDEX idx_activity_log_resource ON audit.activity_log(resource_type, resource_id);
CREATE INDEX idx_activity_log_ip_address ON audit.activity_log(ip_address) WHERE ip_address IS NOT NULL;

-- =====================================================================================
-- CACHE SCHEMA TABLES
-- =====================================================================================

-- -----------------------------------------------------------------------------
-- Query cache table
-- -----------------------------------------------------------------------------
CREATE TABLE cache.query_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    query_hash VARCHAR(64) NOT NULL,
    
    -- Cache data
    result JSONB NOT NULL,
    result_count INTEGER,
    
    -- Metadata
    query_text TEXT,
    query_params JSONB,
    
    -- TTL
    expires_at TIMESTAMPTZ NOT NULL,
    
    -- Usage
    hit_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_cache_hit_count CHECK (hit_count >= 0)
);

-- Indexes for cache
CREATE INDEX idx_cache_expires_at ON cache.query_results(expires_at);
CREATE INDEX idx_cache_query_hash ON cache.query_results(query_hash);

-- =====================================================================================
-- FUNCTIONS AND PROCEDURES
-- =====================================================================================

-- -----------------------------------------------------------------------------
-- Function to update updated_at timestamp
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION core.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update trigger to all tables with updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON core.organizations
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON core.users
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON core.conversations
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at_column();
CREATE TRIGGER update_actions_updated_at BEFORE UPDATE ON core.actions
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at_column();
CREATE TRIGGER update_escalations_updated_at BEFORE UPDATE ON core.escalations
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at_column();
CREATE TRIGGER update_knowledge_entries_updated_at BEFORE UPDATE ON ai.knowledge_entries
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at_column();
CREATE TRIGGER update_intent_patterns_updated_at BEFORE UPDATE ON analytics.intent_patterns
    FOR EACH ROW EXECUTE FUNCTION core.update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Function to automatically create monthly partitions
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION core.create_monthly_partitions()
RETURNS void AS $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    -- Calculate next month's dates
    start_date := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');
    end_date := start_date + INTERVAL '1 month';
    
    -- Create partition for messages
    partition_name := 'messages_' || TO_CHAR(start_date, 'YYYY_MM');
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS core.%I PARTITION OF core.messages FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
    
    -- Create partition for audit log
    partition_name := 'activity_log_' || TO_CHAR(start_date, 'YYYY_MM');
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS audit.%I PARTITION OF audit.activity_log FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;

-- Schedule partition creation (using pg_cron)
SELECT cron.schedule('create-partitions', '0 0 25 * *', 'SELECT core.create_monthly_partitions()');

-- -----------------------------------------------------------------------------
-- Function to calculate conversation statistics
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION core.calculate_conversation_stats(
    p_conversation_id UUID
) RETURNS TABLE (
    total_messages INTEGER,
    user_messages INTEGER,
    ai_messages INTEGER,
    human_agent_messages INTEGER,
    avg_response_time_seconds NUMERIC,
    median_response_time_seconds NUMERIC,
    total_conversation_time_seconds INTEGER,
    unique_intents INTEGER,
    sentiment_trend VARCHAR(20),
    escalation_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH message_stats AS (
        SELECT
            COUNT(*) as total_messages,
            SUM(CASE WHEN sender_type = 'user' THEN 1 ELSE 0 END) as user_messages,
            SUM(CASE WHEN sender_type = 'ai_agent' THEN 1 ELSE 0 END) as ai_messages,
            SUM(CASE WHEN sender_type = 'human_agent' THEN 1 ELSE 0 END) as human_agent_messages,
            COUNT(DISTINCT intent) as unique_intents
        FROM core.messages
        WHERE conversation_id = p_conversation_id
    ),
    response_times AS (
        SELECT
            AVG(EXTRACT(EPOCH FROM (
                LEAD(created_at) OVER (ORDER BY created_at) - created_at
            ))) as avg_response_time,
            PERCENTILE_CONT(0.5) WITHIN GROUP (
                ORDER BY EXTRACT(EPOCH FROM (
                    LEAD(created_at) OVER (ORDER BY created_at) - created_at
                ))
            ) as median_response_time
        FROM core.messages
        WHERE conversation_id = p_conversation_id
    ),
    conversation_time AS (
        SELECT
            EXTRACT(EPOCH FROM (ended_at - started_at))::INTEGER as total_time
        FROM core.conversations
        WHERE id = p_conversation_id
    ),
    sentiment_analysis AS (
        SELECT
            CASE
                WHEN AVG(sentiment_score) > LAG(AVG(sentiment_score)) OVER (ORDER BY DATE_TRUNC('hour', created_at)) 
                THEN 'improving'
                WHEN AVG(sentiment_score) < LAG(AVG(sentiment_score)) OVER (ORDER BY DATE_TRUNC('hour', created_at))
                THEN 'declining'
                ELSE 'stable'
            END as trend
        FROM core.messages
        WHERE conversation_id = p_conversation_id
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY DATE_TRUNC('hour', created_at) DESC
        LIMIT 1
    ),
    escalation_stats AS (
        SELECT COUNT(*) as escalation_count
        FROM core.escalations
        WHERE conversation_id = p_conversation_id
    )
    SELECT
        ms.total_messages::INTEGER,
        ms.user_messages::INTEGER,
        ms.ai_messages::INTEGER,
        ms.human_agent_messages::INTEGER,
        rt.avg_response_time::NUMERIC,
        rt.median_response_time::NUMERIC,
        ct.total_time,
        ms.unique_intents::INTEGER,
        sa.trend,
        es.escalation_count::INTEGER
    FROM message_stats ms
    CROSS JOIN response_times rt
    CROSS JOIN conversation_time ct
    CROSS JOIN sentiment_analysis sa
    CROSS JOIN escalation_stats es;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Procedure to close inactive conversations
-- -----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE core.close_inactive_conversations(
    p_inactive_hours INTEGER DEFAULT 24
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE core.conversations
    SET 
        status = 'abandoned',
        ended_at = CURRENT_TIMESTAMP,
        resolution_time_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at))::INTEGER
    WHERE 
        status IN ('active', 'waiting_for_user')
        AND last_activity_at < CURRENT_TIMESTAMP - (p_inactive_hours || ' hours')::INTERVAL;
        
    COMMIT;
END;
$$;

-- Schedule inactive conversation cleanup (using pg_cron)
SELECT cron.schedule('close-inactive-conversations', '0 */6 * * *', 'CALL core.close_inactive_conversations(24)');

-- -----------------------------------------------------------------------------
-- Function to refresh materialized views
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics.refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.conversation_metrics;
END;
$$ LANGUAGE plpgsql;

-- Schedule materialized view refresh (using pg_cron)
SELECT cron.schedule('refresh-analytics', '*/15 * * * *', 'SELECT analytics.refresh_materialized_views()');

-- =====================================================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================================================

-- Enable RLS on sensitive tables
ALTER TABLE core.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.knowledge_entries ENABLE ROW LEVEL SECURITY;

-- Create policies for organization isolation
CREATE POLICY org_isolation_users ON core.users
    USING (organization_id = current_setting('app.current_org_id')::UUID);

CREATE POLICY org_isolation_conversations ON core.conversations
    USING (organization_id = current_setting('app.current_org_id')::UUID);

CREATE POLICY org_isolation_messages ON core.messages
    USING (organization_id = current_setting('app.current_org_id')::UUID);

CREATE POLICY org_isolation_knowledge ON ai.knowledge_entries
    USING (organization_id = current_setting('app.current_org_id')::UUID);

-- =====================================================================================
-- PERMISSIONS AND ROLES
-- =====================================================================================

-- Create application roles
CREATE ROLE ai_agent_app;
CREATE ROLE ai_agent_admin;
CREATE ROLE ai_agent_readonly;

-- Grant permissions to app role
GRANT CONNECT ON DATABASE ai_customer_service_agent TO ai_agent_app;
GRANT USAGE ON SCHEMA core, ai, analytics, audit, cache TO ai_agent_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core TO ai_agent_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ai TO ai_agent_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA audit TO ai_agent_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA cache TO ai_agent_app;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO ai_agent_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA core, ai, analytics, audit, cache TO ai_agent_app;

-- Grant permissions to admin role
GRANT ALL PRIVILEGES ON DATABASE ai_customer_service_agent TO ai_agent_admin;
GRANT ALL PRIVILEGES ON SCHEMA core, ai, analytics, audit, cache TO ai_agent_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core, ai, analytics, audit, cache TO ai_agent_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA core, ai, analytics, audit, cache TO ai_agent_admin;

-- Grant permissions to readonly role
GRANT CONNECT ON DATABASE ai_customer_service_agent TO ai_agent_readonly;
GRANT USAGE ON SCHEMA core, ai, analytics, audit TO ai_agent_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA core, ai, analytics, audit TO ai_agent_readonly;

-- =====================================================================================
-- INITIAL DATA SEEDING
-- =====================================================================================

-- Insert default organization for development
INSERT INTO core.organizations (
    id,
    name,
    display_name,
    subscription_tier,
    settings,
    features
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'development',
    'Development Organization',
    'enterprise',
    '{"development_mode": true}',
    '{"ai_enabled": true, "escalation_enabled": true, "all_features": true}'
) ON CONFLICT (id) DO NOTHING;

-- =====================================================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================================================

-- Table comments
COMMENT ON TABLE core.organizations IS 'Multi-tenant organizations using the AI customer service agent';
COMMENT ON TABLE core.users IS 'Users within organizations - both customers and agents';
COMMENT ON TABLE core.conversations IS 'Customer service conversations between users and AI/human agents';
COMMENT ON TABLE core.messages IS 'Individual messages within conversations (partitioned by month)';
COMMENT ON TABLE core.actions IS 'Automated actions and tasks performed by the system';
COMMENT ON TABLE core.escalations IS 'Escalated conversations requiring human intervention';
COMMENT ON TABLE ai.knowledge_entries IS 'Knowledge base articles used for AI responses';
COMMENT ON TABLE ai.model_interactions IS 'Tracking of AI model API calls and responses';
COMMENT ON TABLE analytics.intent_patterns IS 'Analyzed patterns of user intents for improvement';
COMMENT ON TABLE audit.activity_log IS 'Comprehensive audit trail of all system activities';

-- Column comments (examples)
COMMENT ON COLUMN core.conversations.ai_confidence_avg IS 'Average AI confidence score across all messages in conversation';
COMMENT ON COLUMN core.messages.embedding IS 'Vector embedding for semantic similarity search';
COMMENT ON COLUMN ai.knowledge_entries.search_vector IS 'Full-text search vector automatically maintained by trigger';

-- =====================================================================================
-- FINAL SETUP
-- =====================================================================================

-- Analyze tables for query planner
ANALYZE;

-- Show final summary
SELECT 
    schemaname,
    COUNT(*) as table_count
FROM pg_tables 
WHERE schemaname IN ('core', 'ai', 'analytics', 'audit', 'cache')
GROUP BY schemaname
ORDER BY schemaname;

-- =====================================================================================
-- END OF SCHEMA DEFINITION
-- =====================================================================================
