-- =====================================================================================
-- AI CUSTOMER SERVICE AGENT - POSTGRESQL v16 DATABASE SCHEMA
-- Version: 4.0.0
-- Description: Unified, production-ready schema combining best of v2 and v3 with PRD v4 deltas
--   - Multi-tenancy with RLS
--   - Partitioned high-volume tables (messages, audit)
--   - Rich conversation/AI observability
--   - RAG-ready knowledge base with vector + FTS
--   - Integration (Salesforce), cache, analytics
--   - Proactive intelligence and compliance modules
-- PostgreSQL Version: 16.x
-- =====================================================================================

-- =====================================================================================
-- DATABASE PARAMETERS (optional guidance; set at DB level as appropriate)
-- =====================================================================================
-- ALTER DATABASE ai_customer_service SET shared_preload_libraries = 'pg_stat_statements,vector';
-- ALTER DATABASE ai_customer_service SET max_connections = 200;
-- ALTER DATABASE ai_customer_service SET shared_buffers = '8GB';
-- ALTER DATABASE ai_customer_service SET effective_cache_size = '24GB';
-- ALTER DATABASE ai_customer_service SET work_mem = '64MB';
-- ALTER DATABASE ai_customer_service SET random_page_cost = 1.1;

-- =====================================================================================
-- EXTENSIONS
-- =====================================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "vector";             -- pgvector for embeddings
-- Optional (uncomment if available):
-- CREATE EXTENSION IF NOT EXISTS "pg_cron";
-- CREATE EXTENSION IF NOT EXISTS "postgres_fdw";
-- CREATE EXTENSION IF NOT EXISTS "pg_partman";
-- CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- =====================================================================================
-- SCHEMAS
-- =====================================================================================
CREATE SCHEMA IF NOT EXISTS core;         COMMENT ON SCHEMA core IS 'Core business entities';
CREATE SCHEMA IF NOT EXISTS ai;           COMMENT ON SCHEMA ai IS 'AI/ML components and data';
CREATE SCHEMA IF NOT EXISTS analytics;    COMMENT ON SCHEMA analytics IS 'Analytics and reporting';
CREATE SCHEMA IF NOT EXISTS audit;        COMMENT ON SCHEMA audit IS 'Audit and compliance logs';
CREATE SCHEMA IF NOT EXISTS cache;        COMMENT ON SCHEMA cache IS 'Performance cache';
CREATE SCHEMA IF NOT EXISTS integration;  COMMENT ON SCHEMA integration IS 'External integrations';
CREATE SCHEMA IF NOT EXISTS monitoring;   COMMENT ON SCHEMA monitoring IS 'Monitoring helper views';

SET search_path TO core, ai, analytics, audit, cache, integration, monitoring, public;

-- =====================================================================================
-- CUSTOM TYPES & DOMAINS
-- =====================================================================================
CREATE TYPE core.subscription_tier AS ENUM ('trial','free','starter','professional','enterprise','custom');
CREATE TYPE core.organization_status AS ENUM ('pending_verification','active','suspended','terminated','churned');

CREATE TYPE core.conversation_status AS ENUM (
  'initialized','active','waiting_for_user','waiting_for_agent','processing','escalated','transferred','resolved','abandoned','archived'
);
CREATE TYPE core.conversation_channel AS ENUM (
  'web_chat','mobile_ios','mobile_android','email','slack','teams','whatsapp','telegram','sms','voice','api','widget','salesforce'
);
CREATE TYPE core.priority_level AS ENUM ('low','medium','high','urgent','critical');

CREATE TYPE core.sentiment_label AS ENUM ('very_negative','negative','neutral','positive','very_positive');
CREATE TYPE core.emotion_label AS ENUM ('angry','frustrated','confused','neutral','satisfied','happy','excited');

CREATE TYPE core.message_sender_type AS ENUM ('user','ai_agent','human_agent','system','bot','integration');
CREATE TYPE core.message_content_type AS ENUM ('text','html','markdown','code','json','image','audio','video','file','card','carousel','quick_reply','form');

CREATE TYPE core.action_status AS ENUM ('pending','scheduled','in_progress','completed','failed','cancelled','timeout','retry');

CREATE TYPE core.escalation_reason AS ENUM (
  'user_requested','sentiment_negative','emotion_angry','low_confidence','multiple_attempts','complex_issue','vip_customer','compliance_required','technical_error','timeout','manual_review'
);

CREATE TYPE ai.model_provider AS ENUM ('openai','anthropic','google','azure','aws','huggingface','cohere','local','custom');
CREATE TYPE ai.model_type AS ENUM ('completion','chat','embedding','classification','sentiment','ner','summarization','translation','code_generation','image_generation');

CREATE DOMAIN core.email AS TEXT CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
CREATE DOMAIN core.url AS TEXT CHECK (VALUE ~* '^https?://[^\s/$.?#].[^\s]*$');
CREATE DOMAIN core.phone AS TEXT CHECK (VALUE ~* '^\+?[1-9]\d{1,14}$');
CREATE DOMAIN core.percentage AS DECIMAL(5,2) CHECK (VALUE >= 0 AND VALUE <= 100);
CREATE DOMAIN core.confidence_score AS DECIMAL(4,3) CHECK (VALUE >= 0 AND VALUE <= 1);
CREATE DOMAIN core.positive_integer AS INTEGER CHECK (VALUE > 0);
CREATE DOMAIN core.non_negative_integer AS INTEGER CHECK (VALUE >= 0);

-- =====================================================================================
-- CORE TABLES
-- =====================================================================================

-- Organizations (tenant root)
CREATE TABLE IF NOT EXISTS core.organizations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug VARCHAR(100) UNIQUE NOT NULL,
  external_id VARCHAR(255) UNIQUE,

  -- Basic info
  name VARCHAR(255) NOT NULL,
  display_name VARCHAR(255),
  description TEXT,
  website core.url,
  logo_url core.url,

  -- Salesforce
  salesforce_org_id VARCHAR(18) UNIQUE,
  salesforce_instance_url core.url,
  salesforce_api_version VARCHAR(10) DEFAULT 'v60.0',

  -- Subscription
  subscription_tier core.subscription_tier NOT NULL DEFAULT 'trial',
  subscription_status core.organization_status NOT NULL DEFAULT 'pending_verification',
  subscription_started_at TIMESTAMPTZ,
  subscription_expires_at TIMESTAMPTZ,
  trial_ends_at TIMESTAMPTZ,
  mrr_amount DECIMAL(10,2),

  -- Limits
  max_users core.positive_integer DEFAULT 10,
  max_conversations_per_month core.positive_integer DEFAULT 1000,
  max_messages_per_conversation core.positive_integer DEFAULT 100,
  max_knowledge_entries core.positive_integer DEFAULT 1000,
  max_api_calls_per_hour core.positive_integer DEFAULT 10000,
  storage_quota_gb core.positive_integer DEFAULT 10,

  -- Usage (maintained by triggers)
  current_users_count core.non_negative_integer DEFAULT 0,
  current_month_conversations core.non_negative_integer DEFAULT 0,
  current_storage_gb DECIMAL(10,3) DEFAULT 0,
  total_conversations_lifetime core.non_negative_integer DEFAULT 0,

  -- Settings & feature flags
  settings JSONB NOT NULL DEFAULT '{
    "ai_enabled": true,
    "auto_escalation": true,
    "sentiment_analysis": true,
    "emotion_detection": true,
    "language_detection": true,
    "profanity_filter": true,
    "auto_translation": false
  }'::jsonb,
  features JSONB NOT NULL DEFAULT '{
    "custom_models": false,
    "white_label": false,
    "sso_enabled": false,
    "api_access": true,
    "webhooks": true,
    "analytics_dashboard": true
  }'::jsonb,
  branding JSONB DEFAULT '{
    "primary_color": "#1976d2",
    "secondary_color": "#dc004e",
    "font_family": "Roboto"
  }'::jsonb,

  -- Localization & security
  timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
  default_language VARCHAR(10) NOT NULL DEFAULT 'en',
  supported_languages TEXT[] DEFAULT ARRAY['en'],
  allowed_domains TEXT[] DEFAULT '{}',
  ip_whitelist INET[] DEFAULT '{}',
  require_mfa BOOLEAN DEFAULT false,

  -- Metadata
  metadata JSONB DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',
  industry VARCHAR(100),
  company_size VARCHAR(50),

  -- Status
  is_active BOOLEAN NOT NULL DEFAULT true,
  is_verified BOOLEAN NOT NULL DEFAULT false,
  is_demo BOOLEAN DEFAULT false,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  verified_at TIMESTAMPTZ,
  last_active_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ,

  CONSTRAINT chk_org_slug_format CHECK (slug ~* '^[a-z0-9][a-z0-9-]*[a-z0-9]$'),
  CONSTRAINT chk_org_usage_limits CHECK (
    current_users_count <= max_users AND
    current_month_conversations <= max_conversations_per_month AND
    current_storage_gb <= storage_quota_gb
  )
);
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON core.organizations(slug) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_organizations_salesforce ON core.organizations(salesforce_org_id) WHERE salesforce_org_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_organizations_subscription ON core.organizations(subscription_tier, subscription_status);
CREATE INDEX IF NOT EXISTS idx_organizations_created ON core.organizations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_organizations_settings_gin ON core.organizations USING gin(settings);
CREATE INDEX IF NOT EXISTS idx_organizations_features_gin ON core.organizations USING gin(features);

-- Users
CREATE TABLE IF NOT EXISTS core.users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  external_id VARCHAR(255),

  -- Auth
  email core.email NOT NULL,
  email_verified BOOLEAN DEFAULT false,
  email_verified_at TIMESTAMPTZ,
  username VARCHAR(100),
  password_hash VARCHAR(255),
  password_changed_at TIMESTAMPTZ,

  -- MFA
  mfa_enabled BOOLEAN DEFAULT false,
  mfa_secret VARCHAR(255),
  mfa_backup_codes TEXT[],
  mfa_last_used_at TIMESTAMPTZ,

  -- Profile
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  display_name VARCHAR(200),
  avatar_url core.url,
  phone_number core.phone,
  phone_verified BOOLEAN DEFAULT false,
  phone_verified_at TIMESTAMPTZ,

  -- Salesforce
  salesforce_user_id VARCHAR(18),
  salesforce_contact_id VARCHAR(18),

  -- RBAC / flags
  role VARCHAR(50) NOT NULL DEFAULT 'customer',
  permissions JSONB DEFAULT '{}',
  is_admin BOOLEAN DEFAULT false,
  is_agent BOOLEAN DEFAULT false,

  -- Customer metrics
  customer_tier VARCHAR(50),
  customer_since DATE,
  lifetime_value DECIMAL(15,2) DEFAULT 0,
  total_conversations core.non_negative_integer DEFAULT 0,

  -- Preferences
  preferred_language VARCHAR(10) DEFAULT 'en',
  preferred_channel core.conversation_channel,
  notification_preferences JSONB DEFAULT '{"email": true, "sms": false, "push": true}'::jsonb,

  -- API access
  api_key VARCHAR(255) UNIQUE,
  api_secret_hash VARCHAR(255),
  api_rate_limit core.positive_integer DEFAULT 1000,
  api_last_used_at TIMESTAMPTZ,

  -- Session/status
  is_active BOOLEAN NOT NULL DEFAULT true,
  is_online BOOLEAN DEFAULT false,
  last_seen_at TIMESTAMPTZ,
  last_ip_address INET,
  last_user_agent TEXT,

  -- Metadata
  attributes JSONB DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMPTZ,

  CONSTRAINT uq_users_org_email UNIQUE (organization_id, email)
);
CREATE INDEX IF NOT EXISTS idx_users_org ON core.users(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_email ON core.users(email) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_username ON core.users(username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON core.users(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_attributes_gin ON core.users USING gin(attributes);

-- Conversations
CREATE TABLE IF NOT EXISTS core.conversations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,

  conversation_number BIGSERIAL UNIQUE,
  external_id VARCHAR(255),
  parent_conversation_id UUID REFERENCES core.conversations(id),
  thread_id UUID,

  title VARCHAR(500),
  description TEXT,
  channel core.conversation_channel NOT NULL,
  source VARCHAR(100),
  source_url core.url,

  status core.conversation_status NOT NULL DEFAULT 'initialized',
  previous_status core.conversation_status,
  status_changed_at TIMESTAMPTZ,
  priority core.priority_level DEFAULT 'medium',
  is_urgent BOOLEAN DEFAULT false,

  assigned_agent_id UUID REFERENCES core.users(id),
  assigned_team VARCHAR(100),
  assigned_queue VARCHAR(100),
  assigned_at TIMESTAMPTZ,
  assignment_method VARCHAR(50),

  started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  first_message_at TIMESTAMPTZ,
  first_response_at TIMESTAMPTZ,
  last_message_at TIMESTAMPTZ,
  last_agent_message_at TIMESTAMPTZ,
  last_user_message_at TIMESTAMPTZ,
  last_activity_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at TIMESTAMPTZ,

  message_count core.non_negative_integer DEFAULT 0,
  user_message_count core.non_negative_integer DEFAULT 0,
  agent_message_count core.non_negative_integer DEFAULT 0,
  ai_message_count core.non_negative_integer DEFAULT 0,

  first_response_time INTEGER,
  average_response_time INTEGER,
  max_response_time INTEGER,

  ai_handled BOOLEAN DEFAULT true,
  ai_confidence_avg core.confidence_score,
  ai_confidence_min core.confidence_score,
  ai_confidence_max core.confidence_score,
  ai_resolution_score core.percentage,
  ai_fallback_count core.non_negative_integer DEFAULT 0,
  ai_retry_count core.non_negative_integer DEFAULT 0,

  sentiment_initial core.sentiment_label,
  sentiment_current core.sentiment_label DEFAULT 'neutral',
  sentiment_final core.sentiment_label,
  sentiment_trend VARCHAR(20),
  sentiment_score_initial DECIMAL(3,2),
  sentiment_score_current DECIMAL(3,2),
  sentiment_score_final DECIMAL(3,2),

  emotion_initial core.emotion_label,
  emotion_current core.emotion_label DEFAULT 'neutral',
  emotion_final core.emotion_label,
  emotion_trajectory JSONB DEFAULT '[]',

  primary_intent VARCHAR(100),
  intent_confidence core.confidence_score,
  secondary_intents TEXT[],
  intent_changed_count core.non_negative_integer DEFAULT 0,

  resolved BOOLEAN DEFAULT false,
  resolved_by VARCHAR(50),
  resolved_at TIMESTAMPTZ,
  resolution_time_seconds INTEGER,
  resolution_summary TEXT,
  resolution_code VARCHAR(50),
  resolution_metadata JSONB DEFAULT '{}',

  escalated BOOLEAN DEFAULT false,
  escalation_reason core.escalation_reason,
  escalated_at TIMESTAMPTZ,
  escalation_count core.non_negative_integer DEFAULT 0,

  transferred BOOLEAN DEFAULT false,
  transferred_count core.non_negative_integer DEFAULT 0,
  transfer_history JSONB DEFAULT '[]',

  satisfaction_score DECIMAL(2,1),
  satisfaction_feedback TEXT,
  nps_score INTEGER,
  csat_score core.percentage,

  language VARCHAR(10) DEFAULT 'en',
  detected_languages TEXT[],

  context JSONB NOT NULL DEFAULT '{}',
  context_variables JSONB DEFAULT '{}',
  session_data JSONB DEFAULT '{}',

  salesforce_case_id VARCHAR(18),
  salesforce_case_number VARCHAR(50),

  category VARCHAR(100),
  subcategory VARCHAR(100),
  tags TEXT[] DEFAULT '{}',
  labels JSONB DEFAULT '{}',
  custom_fields JSONB DEFAULT '{}',

  metadata JSONB DEFAULT '{}',
  browser_info JSONB DEFAULT '{}',
  device_info JSONB DEFAULT '{}',
  location_info JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  archived_at TIMESTAMPTZ,

  CONSTRAINT chk_conv_satisfaction CHECK (satisfaction_score IS NULL OR (satisfaction_score BETWEEN 1 AND 5)),
  CONSTRAINT chk_conv_nps CHECK (nps_score IS NULL OR (nps_score BETWEEN 0 AND 10)),
  CONSTRAINT chk_conv_sentiment CHECK (
    (sentiment_score_initial IS NULL OR (sentiment_score_initial BETWEEN -1 AND 1)) AND
    (sentiment_score_current IS NULL OR (sentiment_score_current BETWEEN -1 AND 1)) AND
    (sentiment_score_final IS NULL OR (sentiment_score_final BETWEEN -1 AND 1))
  ),
  CONSTRAINT chk_conv_ended CHECK (ended_at IS NULL OR ended_at >= started_at),
  CONSTRAINT chk_conv_resolved CHECK ((resolved = false) OR (resolved = true AND resolved_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_conversations_org ON core.conversations(organization_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON core.conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON core.conversations(status) WHERE status NOT IN ('resolved','archived');
CREATE INDEX IF NOT EXISTS idx_conversations_channel_status ON core.conversations(channel, status);
CREATE INDEX IF NOT EXISTS idx_conversations_priority ON core.conversations(priority DESC, created_at DESC) WHERE priority IN ('urgent','critical');
CREATE INDEX IF NOT EXISTS idx_conversations_activity ON core.conversations(last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_salesforce ON core.conversations(salesforce_case_id) WHERE salesforce_case_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_intent ON core.conversations(primary_intent) WHERE primary_intent IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_context_gin ON core.conversations USING gin(context);
CREATE INDEX IF NOT EXISTS idx_conversations_labels_gin ON core.conversations USING gin(labels);

-- Messages (partitioned by created_at)
CREATE TABLE IF NOT EXISTS core.messages (
  id UUID DEFAULT uuid_generate_v4(),
  conversation_id UUID NOT NULL,
  organization_id UUID NOT NULL,

  message_number BIGINT,
  external_id VARCHAR(255),

  sender_type core.message_sender_type NOT NULL,
  sender_id UUID,
  sender_name VARCHAR(255),
  sender_email core.email,
  sender_avatar_url core.url,

  content TEXT NOT NULL,
  content_type core.message_content_type DEFAULT 'text',
  content_encrypted BOOLEAN DEFAULT false,
  content_preview VARCHAR(200),
  content_length INTEGER,

  content_html TEXT,
  content_markdown TEXT,
  content_json JSONB,

  original_language VARCHAR(10),
  detected_language VARCHAR(10),
  content_translated TEXT,
  translated_to VARCHAR(10),
  translation_confidence core.confidence_score,

  intent VARCHAR(100),
  intent_confidence core.confidence_score,
  secondary_intents JSONB DEFAULT '[]',
  intent_parameters JSONB DEFAULT '{}',

  entities JSONB DEFAULT '[]',
  keywords TEXT[],
  topics TEXT[],
  named_entities JSONB DEFAULT '[]',

  sentiment_score DECIMAL(3,2),
  sentiment_label core.sentiment_label,
  sentiment_confidence core.confidence_score,

  emotion_label core.emotion_label,
  emotion_intensity core.confidence_score,
  emotion_indicators TEXT[],

  ai_processed BOOLEAN DEFAULT false,
  ai_model_used VARCHAR(100),
  ai_model_version VARCHAR(50),
  ai_provider ai.model_provider,
  ai_processing_time_ms INTEGER,
  ai_tokens_used INTEGER,
  ai_cost DECIMAL(10,6),
  ai_confidence core.confidence_score,

  is_flagged BOOLEAN DEFAULT false,
  flagged_reason VARCHAR(255),
  flagged_at TIMESTAMPTZ,
  flagged_by UUID,
  moderation_scores JSONB,
  requires_review BOOLEAN DEFAULT false,
  reviewed_at TIMESTAMPTZ,
  reviewed_by UUID,

  is_internal BOOLEAN DEFAULT false,
  is_automated BOOLEAN DEFAULT false,
  is_system_generated BOOLEAN DEFAULT false,
  is_private BOOLEAN DEFAULT false,
  is_whisper BOOLEAN DEFAULT false,

  is_edited BOOLEAN DEFAULT false,
  edited_at TIMESTAMPTZ,
  edited_by UUID,
  edit_count core.non_negative_integer DEFAULT 0,
  edit_history JSONB DEFAULT '[]',

  is_deleted BOOLEAN DEFAULT false,
  deleted_at TIMESTAMPTZ,
  deleted_by UUID,
  deletion_reason VARCHAR(255),

  in_reply_to UUID,
  thread_id UUID,
  thread_position INTEGER,
  is_thread_start BOOLEAN DEFAULT false,

  has_attachments BOOLEAN DEFAULT false,
  attachments JSONB DEFAULT '[]',
  attachment_count core.non_negative_integer DEFAULT 0,
  total_attachment_size_bytes BIGINT DEFAULT 0,

  quick_replies JSONB,
  actions JSONB,
  cards JSONB,

  delivered_at TIMESTAMPTZ,
  delivered_to UUID[],
  seen_at TIMESTAMPTZ,
  seen_by UUID[],
  failed_delivery BOOLEAN DEFAULT false,
  delivery_attempts core.non_negative_integer DEFAULT 0,

  metadata JSONB DEFAULT '{}',
  processing_metadata JSONB DEFAULT '{}',
  client_metadata JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sent_at TIMESTAMPTZ,

  PRIMARY KEY (id, created_at),
  FOREIGN KEY (conversation_id) REFERENCES core.conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (organization_id) REFERENCES core.organizations(id) ON DELETE CASCADE,
  FOREIGN KEY (sender_id) REFERENCES core.users(id) ON DELETE SET NULL,

  CONSTRAINT chk_messages_sentiment CHECK (sentiment_score IS NULL OR (sentiment_score BETWEEN -1 AND 1)),
  CONSTRAINT chk_messages_attachments CHECK (attachment_count >= 0 AND total_attachment_size_bytes >= 0),
  CONSTRAINT chk_messages_tokens CHECK (ai_tokens_used IS NULL OR ai_tokens_used >= 0),
  CONSTRAINT chk_messages_cost CHECK (ai_cost IS NULL OR ai_cost >= 0),
  CONSTRAINT chk_messages_processing_time CHECK (ai_processing_time_ms IS NULL OR ai_processing_time_ms >= 0),
  CONSTRAINT chk_messages_content_length CHECK (content_length IS NULL OR content_length >= 0)
) PARTITION BY RANGE (created_at);

-- Example partitions (add scheduler to auto-create monthly)
CREATE TABLE IF NOT EXISTS core.messages_2024_12 PARTITION OF core.messages FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE IF NOT EXISTS core.messages_default PARTITION OF core.messages DEFAULT;

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON core.messages(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_organization ON core.messages(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON core.messages(sender_type, sender_id) WHERE sender_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_intent ON core.messages(intent) WHERE intent IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_sentiment ON core.messages(sentiment_label) WHERE sentiment_label IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_emotion ON core.messages(emotion_label) WHERE emotion_label IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_thread ON core.messages(thread_id, thread_position) WHERE thread_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_entities_gin ON core.messages USING gin(entities);
CREATE INDEX IF NOT EXISTS idx_messages_keywords_gin ON core.messages USING gin(keywords);
CREATE INDEX IF NOT EXISTS idx_messages_metadata_gin ON core.messages USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_messages_content_trgm ON core.messages USING gin(content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_messages_content_fts ON core.messages USING gin(to_tsvector('english', content));

-- =====================================================================================
-- AI / RAG TABLES
-- =====================================================================================

-- Knowledge entries (multi-embedding + workflow + quality)
CREATE TABLE IF NOT EXISTS ai.knowledge_entries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,

  title VARCHAR(500) NOT NULL,
  content TEXT NOT NULL,
  summary TEXT,
  excerpt VARCHAR(500),
  content_hash VARCHAR(64),

  category VARCHAR(100) NOT NULL,
  subcategory VARCHAR(100),
  topic VARCHAR(100),
  domain VARCHAR(100),
  content_type VARCHAR(50),

  keywords TEXT[],
  tags TEXT[] DEFAULT '{}',
  entities JSONB DEFAULT '[]',
  concepts TEXT[],

  version INTEGER NOT NULL DEFAULT 1,
  is_current BOOLEAN DEFAULT true,
  is_published BOOLEAN DEFAULT false,
  is_draft BOOLEAN DEFAULT true,
  parent_id UUID REFERENCES ai.knowledge_entries(id),
  version_notes TEXT,

  source_type VARCHAR(50),
  source_name VARCHAR(255),
  source_url core.url,
  source_document_id VARCHAR(255),
  author VARCHAR(255),
  author_id UUID REFERENCES core.users(id),
  last_synced_at TIMESTAMPTZ,
  sync_status VARCHAR(50),

  quality_score core.percentage DEFAULT 100,
  confidence_score core.confidence_score DEFAULT 1.0,
  accuracy_score core.percentage,
  completeness_score core.percentage,
  relevance_score core.percentage,
  freshness_score core.percentage,

  view_count core.non_negative_integer DEFAULT 0,
  usage_count core.non_negative_integer DEFAULT 0,
  helpful_count core.non_negative_integer DEFAULT 0,
  not_helpful_count core.non_negative_integer DEFAULT 0,
  feedback_score DECIMAL(3,2),
  last_used_at TIMESTAMPTZ,
  usage_trend VARCHAR(20),

  resolution_rate core.percentage,
  escalation_prevention_rate core.percentage,
  average_confidence_when_used core.confidence_score,

  valid_from TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  valid_until TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  requires_review BOOLEAN DEFAULT false,
  review_date DATE,
  update_frequency_days INTEGER,
  last_reviewed_at TIMESTAMPTZ,

  embedding vector(1536),
  embedding_model VARCHAR(100),
  embedding_version VARCHAR(50),
  embedding_generated_at TIMESTAMPTZ,
  embedding_768 vector(768),
  embedding_1024 vector(1024),

  search_vector tsvector,
  search_rank DECIMAL(10,6),
  boost_factor DECIMAL(3,2) DEFAULT 1.0,

  status VARCHAR(50) DEFAULT 'draft',
  reviewed_by UUID REFERENCES core.users(id),
  reviewed_at TIMESTAMPTZ,
  review_notes TEXT,
  approved_by UUID REFERENCES core.users(id),
  approved_at TIMESTAMPTZ,
  published_by UUID REFERENCES core.users(id),
  published_at TIMESTAMPTZ,

  related_entries UUID[],
  prerequisite_entries UUID[],
  supersedes UUID REFERENCES ai.knowledge_entries(id),
  superseded_by UUID REFERENCES ai.knowledge_entries(id),

  metadata JSONB DEFAULT '{}',
  attachments JSONB DEFAULT '[]',
  references JSONB DEFAULT '[]',

  access_level VARCHAR(50) DEFAULT 'public',
  allowed_roles TEXT[],
  allowed_users UUID[],

  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  archived_at TIMESTAMPTZ,

  CONSTRAINT chk_knowledge_version CHECK (version > 0),
  CONSTRAINT chk_knowledge_scores CHECK (
    (quality_score IS NULL OR quality_score BETWEEN 0 AND 100) AND
    (accuracy_score IS NULL OR accuracy_score BETWEEN 0 AND 100) AND
    (completeness_score IS NULL OR completeness_score BETWEEN 0 AND 100) AND
    (relevance_score IS NULL OR relevance_score BETWEEN 0 AND 100) AND
    (freshness_score IS NULL OR freshness_score BETWEEN 0 AND 100)
  ),
  CONSTRAINT chk_knowledge_feedback CHECK (feedback_score IS NULL OR feedback_score BETWEEN -1 AND 1),
  CONSTRAINT uq_knowledge_content_hash UNIQUE (organization_id, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_org ON ai.knowledge_entries(organization_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON ai.knowledge_entries(category, subcategory);
CREATE INDEX IF NOT EXISTS idx_knowledge_status ON ai.knowledge_entries(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_current ON ai.knowledge_entries(is_current, is_published) WHERE is_current = true AND is_published = true;
CREATE INDEX IF NOT EXISTS idx_knowledge_search ON ai.knowledge_entries USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_1536 ON ai.knowledge_entries USING ivfflat (embedding vector_cosine_ops) WHERE embedding IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_768 ON ai.knowledge_entries USING ivfflat (embedding_768 vector_cosine_ops) WHERE embedding_768 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_1024 ON ai.knowledge_entries USING ivfflat (embedding_1024 vector_cosine_ops) WHERE embedding_1024 IS NOT NULL;

-- Model interactions (AI observability)
CREATE TABLE IF NOT EXISTS ai.model_interactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES core.conversations(id) ON DELETE CASCADE,
  message_id UUID,
  user_id UUID REFERENCES core.users(id),

  model_provider ai.model_provider NOT NULL,
  model_name VARCHAR(100) NOT NULL,
  model_version VARCHAR(50),
  model_type ai.model_type NOT NULL,
  endpoint_url core.url,

  request_id VARCHAR(255) UNIQUE,
  request_type VARCHAR(50),
  prompt TEXT,
  system_prompt TEXT,
  messages JSONB,

  parameters JSONB DEFAULT '{"temperature":0.7,"max_tokens":500}'::jsonb,

  response TEXT,
  response_object JSONB,
  response_id VARCHAR(255),
  finish_reason VARCHAR(50),

  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  total_tokens INTEGER,

  latency_ms INTEGER,
  time_to_first_token_ms INTEGER,
  tokens_per_second DECIMAL(10,2),

  confidence_score core.confidence_score,
  perplexity DECIMAL(10,4),

  prompt_cost DECIMAL(10,6),
  completion_cost DECIMAL(10,6),
  total_cost DECIMAL(10,6),

  success BOOLEAN DEFAULT true,
  error_type VARCHAR(50),
  error_message TEXT,
  error_code VARCHAR(50),
  retry_count core.non_negative_integer DEFAULT 0,
  retried_from UUID REFERENCES ai.model_interactions(id),

  cache_hit BOOLEAN DEFAULT false,
  cache_key VARCHAR(255),
  cached_at TIMESTAMPTZ,
  cache_ttl_seconds INTEGER,

  metadata JSONB DEFAULT '{}',
  request_headers JSONB DEFAULT '{}',
  response_headers JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT chk_model_tokens CHECK (
    (prompt_tokens IS NULL OR prompt_tokens >= 0) AND
    (completion_tokens IS NULL OR completion_tokens >= 0) AND
    (total_tokens IS NULL OR total_tokens >= 0)
  ),
  CONSTRAINT chk_model_cost CHECK (
    (prompt_cost IS NULL OR prompt_cost >= 0) AND
    (completion_cost IS NULL OR completion_cost >= 0) AND
    (total_cost IS NULL OR total_cost >= 0)
  ),
  CONSTRAINT chk_model_latency CHECK (latency_ms IS NULL OR latency_ms >= 0)
);
CREATE INDEX IF NOT EXISTS idx_model_interactions_org ON ai.model_interactions(organization_id);
CREATE INDEX IF NOT EXISTS idx_model_interactions_conv ON ai.model_interactions(conversation_id) WHERE conversation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_model_interactions_provider_model ON ai.model_interactions(model_provider, model_name);
CREATE INDEX IF NOT EXISTS idx_model_interactions_created ON ai.model_interactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_model_interactions_success ON ai.model_interactions(success, error_type) WHERE success = false;

-- =====================================================================================
-- ANALYTICS
-- =====================================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.conversation_metrics AS
WITH hourly AS (
  SELECT
    DATE_TRUNC('hour', c.started_at) AS hour,
    c.organization_id,
    c.channel,
    c.status,
    c.priority,
    COUNT(DISTINCT c.id) AS conversation_count,
    COUNT(*) FILTER (WHERE c.resolved = true) AS resolved_count,
    COUNT(*) FILTER (WHERE c.escalated = true) AS escalated_count,
    COUNT(*) FILTER (WHERE c.ai_handled = true) AS ai_handled_count,
    AVG(c.resolution_time_seconds) FILTER (WHERE c.resolution_time_seconds IS NOT NULL) AS avg_resolution_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY c.resolution_time_seconds)
      FILTER (WHERE c.resolution_time_seconds IS NOT NULL) AS p95_resolution_time,
    AVG(c.first_response_time) FILTER (WHERE c.first_response_time IS NOT NULL) AS avg_first_response_time,
    AVG(c.message_count) AS avg_message_count,
    SUM(c.message_count) AS total_messages,
    AVG(c.ai_confidence_avg) FILTER (WHERE c.ai_confidence_avg IS NOT NULL) AS avg_ai_confidence,
    MIN(c.ai_confidence_min) FILTER (WHERE c.ai_confidence_min IS NOT NULL) AS min_ai_confidence,
    AVG(c.satisfaction_score) FILTER (WHERE c.satisfaction_score IS NOT NULL) AS avg_satisfaction_score
  FROM core.conversations c
  WHERE c.started_at >= CURRENT_DATE - INTERVAL '90 days'
  GROUP BY 1,2,3,4,5
)
SELECT
  *,
  CASE WHEN conversation_count > 0 THEN (resolved_count::DECIMAL / conversation_count * 100)::DECIMAL(5,2) ELSE 0 END AS resolution_rate,
  CASE WHEN conversation_count > 0 THEN (escalated_count::DECIMAL / conversation_count * 100)::DECIMAL(5,2) ELSE 0 END AS escalation_rate,
  CASE WHEN conversation_count > 0 THEN (ai_handled_count::DECIMAL / conversation_count * 100)::DECIMAL(5,2) ELSE 0 END AS ai_coverage_rate
FROM hourly
WITH DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_conv_metrics_unique ON analytics.conversation_metrics(hour, organization_id, channel, status, priority);
CREATE INDEX IF NOT EXISTS idx_conv_metrics_org_hour ON analytics.conversation_metrics(organization_id, hour DESC);

-- =====================================================================================
-- AUDIT
-- =====================================================================================
CREATE TABLE IF NOT EXISTS audit.activity_log (
  id UUID DEFAULT uuid_generate_v4(),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

  organization_id UUID,
  user_id UUID,
  user_email VARCHAR(255),
  user_role VARCHAR(50),
  impersonated_by UUID,
  service_account VARCHAR(255),

  action VARCHAR(100) NOT NULL,
  action_category VARCHAR(50),
  resource_type VARCHAR(50),
  resource_id UUID,
  resource_name VARCHAR(255),

  old_values JSONB,
  new_values JSONB,
  changed_fields TEXT[],
  change_summary TEXT,

  request_id VARCHAR(255),
  session_id VARCHAR(255),
  correlation_id VARCHAR(255),
  ip_address INET,
  user_agent TEXT,
  referer TEXT,

  status_code INTEGER,
  success BOOLEAN DEFAULT true,
  error_message TEXT,
  error_details JSONB,
  duration_ms INTEGER,

  metadata JSONB DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',

  PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Example partitions
CREATE TABLE IF NOT EXISTS audit.activity_log_2024_12 PARTITION OF audit.activity_log FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit.activity_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit.activity_log(organization_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit.activity_log(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit.activity_log(action, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit.activity_log(resource_type, resource_id);

-- =====================================================================================
-- INTEGRATION (Salesforce example)
-- =====================================================================================
CREATE TABLE IF NOT EXISTS integration.salesforce_sync (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,

  sync_type VARCHAR(50) NOT NULL,            -- case, contact, account...
  sync_direction VARCHAR(20) NOT NULL,       -- inbound, outbound, bidirectional

  local_object_type VARCHAR(50) NOT NULL,
  local_object_id UUID NOT NULL,
  salesforce_object_type VARCHAR(50) NOT NULL,
  salesforce_object_id VARCHAR(18) NOT NULL,

  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  last_sync_at TIMESTAMPTZ,
  next_sync_at TIMESTAMPTZ,
  sync_frequency_minutes INTEGER DEFAULT 15,

  local_updated_at TIMESTAMPTZ,
  salesforce_updated_at TIMESTAMPTZ,
  changes_detected BOOLEAN DEFAULT false,

  error_count core.non_negative_integer DEFAULT 0,
  last_error_at TIMESTAMPTZ,
  last_error_message TEXT,

  field_mappings JSONB NOT NULL DEFAULT '{}',
  sync_metadata JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT uq_salesforce_sync UNIQUE (organization_id, local_object_type, local_object_id),
  CONSTRAINT uq_salesforce_object UNIQUE (organization_id, salesforce_object_type, salesforce_object_id)
);
CREATE INDEX IF NOT EXISTS idx_salesforce_sync_org ON integration.salesforce_sync(organization_id);
CREATE INDEX IF NOT EXISTS idx_salesforce_sync_status ON integration.salesforce_sync(status);

-- =====================================================================================
-- CACHE
-- =====================================================================================
CREATE TABLE IF NOT EXISTS cache.query_results (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  cache_key VARCHAR(255) UNIQUE NOT NULL,
  query_hash VARCHAR(64) NOT NULL,

  result_data JSONB NOT NULL,
  result_count INTEGER,
  result_size_bytes INTEGER,
  compression_ratio DECIMAL(3,2),

  query_text TEXT,
  query_params JSONB,
  query_duration_ms INTEGER,

  cache_ttl_seconds INTEGER NOT NULL DEFAULT 300,
  expires_at TIMESTAMPTZ NOT NULL,
  is_stale BOOLEAN DEFAULT false,

  hit_count core.non_negative_integer DEFAULT 0,
  last_hit_at TIMESTAMPTZ,
  avg_retrieval_ms INTEGER,

  created_by VARCHAR(255),
  tags TEXT[] DEFAULT '{}',

  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_cache_key ON cache.query_results(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache.query_results(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_hash ON cache.query_results(query_hash);

-- =====================================================================================
-- PROACTIVE INTELLIGENCE (New in v4)
-- =====================================================================================
CREATE TABLE IF NOT EXISTS ai.org_health_snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  health_score core.percentage,
  metrics JSONB DEFAULT '{}',               -- aggregated KPIs, latency, errors, etc.
  detected_patterns JSONB DEFAULT '[]',     -- patterns identified
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_org_health_org ON ai.org_health_snapshots(organization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ai.proactive_predictions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  type VARCHAR(50) NOT NULL,                -- governor_limits, cpu_time, api_limits, etc.
  signal_source VARCHAR(50),                -- metrics, logs, external
  predicted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  prediction_window INTERVAL,
  risk_score core.percentage,
  confidence core.confidence_score,
  recommended_action TEXT,
  remediation_level VARCHAR(20),            -- low, medium, high
  status VARCHAR(20) DEFAULT 'open',        -- open, actioned, dismissed
  metadata JSONB DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_proactive_org ON ai.proactive_predictions(organization_id, predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_proactive_type ON ai.proactive_predictions(type);

CREATE TABLE IF NOT EXISTS ai.proactive_actions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  prediction_id UUID REFERENCES ai.proactive_predictions(id) ON DELETE SET NULL,
  action_type VARCHAR(50) NOT NULL,         -- throttle, cache_warm, pre_scale, notify, etc.
  params JSONB DEFAULT '{}',
  is_safe BOOLEAN DEFAULT true,
  executed_at TIMESTAMPTZ,
  success BOOLEAN,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_proactive_actions_org ON ai.proactive_actions(organization_id, created_at DESC);

-- =====================================================================================
-- COMPLIANCE MODULES (New in v4)
-- =====================================================================================
CREATE TABLE IF NOT EXISTS audit.compliance_checks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  module VARCHAR(50) NOT NULL,              -- hipaa, pci, fedramp, gdpr
  operation VARCHAR(50) NOT NULL,           -- read, write, export, delete
  data_ref TEXT,                            -- reference to data object
  result VARCHAR(20) NOT NULL,              -- pass, fail, warn
  violations JSONB DEFAULT '[]',
  can_remediate BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_org ON audit.compliance_checks(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_module ON audit.compliance_checks(module, result);

CREATE TABLE IF NOT EXISTS audit.compliance_audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  module VARCHAR(50) NOT NULL,
  action VARCHAR(100) NOT NULL,
  actor VARCHAR(255),
  details JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_compliance_audit_org ON audit.compliance_audit_log(organization_id, created_at DESC);

-- =====================================================================================
-- FUNCTIONS & TRIGGERS
-- =====================================================================================

-- Universal updated_at trigger
CREATE OR REPLACE FUNCTION core.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

-- Apply to tables with updated_at
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT schemaname, tablename
    FROM pg_tables
    WHERE schemaname IN ('core','ai','analytics','audit','cache','integration')
      AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = schemaname
          AND table_name = tablename
          AND column_name = 'updated_at'
      )
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trigger_update_%I_updated_at ON %I.%I', r.tablename, r.schemaname, r.tablename);
    EXECUTE format('CREATE TRIGGER trigger_update_%I_updated_at BEFORE UPDATE ON %I.%I FOR EACH ROW EXECUTE FUNCTION core.update_updated_at()', r.tablename, r.schemaname, r.tablename);
  END LOOP;
END $$;

-- Conversation metrics update on message insert
CREATE OR REPLACE FUNCTION core.update_conversation_metrics()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE core.conversations
  SET
    message_count = message_count + 1,
    user_message_count = user_message_count + CASE WHEN NEW.sender_type = 'user' THEN 1 ELSE 0 END,
    agent_message_count = agent_message_count + CASE WHEN NEW.sender_type IN ('human_agent','ai_agent') THEN 1 ELSE 0 END,
    ai_message_count = ai_message_count + CASE WHEN NEW.sender_type = 'ai_agent' THEN 1 ELSE 0 END,
    last_activity_at = NEW.created_at,
    last_message_at = NEW.created_at,
    last_user_message_at = CASE WHEN NEW.sender_type = 'user' THEN NEW.created_at ELSE last_user_message_at END,
    last_agent_message_at = CASE WHEN NEW.sender_type IN ('human_agent','ai_agent') THEN NEW.created_at ELSE last_agent_message_at END,
    first_message_at = COALESCE(first_message_at, NEW.created_at),
    first_response_at = CASE WHEN first_response_at IS NULL AND NEW.sender_type IN ('human_agent','ai_agent') THEN NEW.created_at ELSE first_response_at END
  WHERE id = NEW.conversation_id;

  IF NEW.sentiment_label IS NOT NULL THEN
    UPDATE core.conversations
    SET sentiment_current = NEW.sentiment_label,
        sentiment_score_current = NEW.sentiment_score
    WHERE id = NEW.conversation_id;
  END IF;

  IF NEW.emotion_label IS NOT NULL THEN
    UPDATE core.conversations
    SET emotion_current = NEW.emotion_label,
        emotion_trajectory = emotion_trajectory ||
          jsonb_build_object('timestamp', NEW.created_at, 'emotion', NEW.emotion_label, 'intensity', NEW.emotion_intensity)
    WHERE id = NEW.conversation_id;
  END IF;

  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_conversation_metrics ON core.messages;
CREATE TRIGGER trigger_update_conversation_metrics
AFTER INSERT ON core.messages
FOR EACH ROW EXECUTE FUNCTION core.update_conversation_metrics();

-- Optional: Monthly partition creation (messages & audit)
CREATE OR REPLACE FUNCTION core.create_monthly_partitions()
RETURNS void AS $$
DECLARE start_date DATE; end_date DATE; part_name TEXT;
BEGIN
  start_date := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');
  end_date := start_date + INTERVAL '1 month';

  part_name := 'messages_' || TO_CHAR(start_date, 'YYYY_MM');
  EXECUTE format('CREATE TABLE IF NOT EXISTS core.%I PARTITION OF core.messages FOR VALUES FROM (%L) TO (%L)', part_name, start_date, end_date);

  part_name := 'activity_log_' || TO_CHAR(start_date, 'YYYY_MM');
  EXECUTE format('CREATE TABLE IF NOT EXISTS audit.%I PARTITION OF audit.activity_log FOR VALUES FROM (%L) TO (%L)', part_name, start_date, end_date);
END; $$ LANGUAGE plpgsql;

-- Optional: MV refresh
CREATE OR REPLACE PROCEDURE analytics.refresh_views()
LANGUAGE plpgsql AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.conversation_metrics;
END $$;

-- =====================================================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================================================
ALTER TABLE core.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.knowledge_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.model_interactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation_users ON core.users
  USING (organization_id = COALESCE(current_setting('app.current_org_id', true)::UUID, organization_id));
CREATE POLICY org_isolation_conversations ON core.conversations
  USING (organization_id = COALESCE(current_setting('app.current_org_id', true)::UUID, organization_id));
CREATE POLICY org_isolation_messages ON core.messages
  USING (organization_id = COALESCE(current_setting('app.current_org_id', true)::UUID, organization_id));
CREATE POLICY org_isolation_knowledge ON ai.knowledge_entries
  USING (organization_id = COALESCE(current_setting('app.current_org_id', true)::UUID, organization_id));
CREATE POLICY org_isolation_model_interactions ON ai.model_interactions
  USING (organization_id = COALESCE(current_setting('app.current_org_id', true)::UUID, organization_id));

-- =====================================================================================
-- ROLES & GRANTS (adjust to environment)
-- =====================================================================================
-- DO $$ BEGIN
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ai_agent_app') THEN CREATE ROLE ai_agent_app LOGIN; END IF;
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ai_agent_readonly') THEN CREATE ROLE ai_agent_readonly LOGIN; END IF;
--   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ai_agent_admin') THEN CREATE ROLE ai_agent_admin LOGIN; END IF;
-- END $$;
-- GRANT USAGE ON SCHEMA core, ai, analytics, audit, cache, integration TO ai_agent_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core, ai, cache, integration TO ai_agent_app;
-- GRANT SELECT ON ALL TABLES IN SCHEMA analytics, audit TO ai_agent_app;
-- GRANT SELECT ON ALL TABLES IN SCHEMA core, ai, analytics, audit TO ai_agent_readonly;
-- GRANT ALL ON SCHEMAS core, ai, analytics, audit, cache, integration TO ai_agent_admin;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core, ai, analytics, audit, cache, integration TO ai_agent_admin;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA core, ai, analytics, audit, cache, integration GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ai_agent_app;

-- =====================================================================================
-- MONITORING VIEWS
-- =====================================================================================
CREATE OR REPLACE VIEW monitoring.table_sizes AS
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname IN ('core','ai','analytics','audit','cache','integration')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

CREATE OR REPLACE VIEW monitoring.index_usage AS
SELECT
  schemaname, tablename, indexname,
  idx_scan AS index_scans, idx_tup_read AS tuples_read, idx_tup_fetch AS tuples_fetched,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname IN ('core','ai','analytics','audit','cache','integration')
ORDER BY idx_scan DESC;

CREATE OR REPLACE VIEW monitoring.slow_queries AS
SELECT calls,
       mean_exec_time::numeric(10,2) AS avg_ms,
       max_exec_time::numeric(10,2) AS max_ms,
       total_exec_time::numeric(10,2) AS total_ms,
       LEFT(query, 100) AS query_preview
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 20;

-- =====================================================================================
-- OPTIONAL SCHEDULING (requires pg_cron)
-- =====================================================================================
-- SELECT cron.schedule('refresh-analytics', '*/15 * * * *', 'CALL analytics.refresh_views()');
-- SELECT cron.schedule('create-partitions',  '0 0 25 * *',  'SELECT core.create_monthly_partitions()');

-- =====================================================================================
-- END OF SCHEMA v4.0.0
-- =====================================================================================
