### Deep-Dive Comparative Assessment: `database schema v2.sql` vs `database schema v3.sql` (Validated Against PRD v4)

#### Methodology (Plan First)
- Establish PRD v4 alignment lenses:
  - Multi-tenancy and data isolation (RLS), role-based access, auditability.
  - Conversation lifecycle and analytics (KPIs, performance metrics, escalation/SLA, sentiment/emotion).
  - AI/LLM observability (tokens, latency, cost, confidence, retries/fallbacks), RAG readiness (vector + FTS).
  - Integrations (Salesforce sync, external systems), caching, partitioning and scalability.
  - Security/compliance (audit trail, PII handling hints, module toggles), operational maintainability (partitions, cron, views).
- Evaluate each schema across: schemas/types/domains, core tables, AI/RAG, analytics, audit, cache, integration, RLS/roles, triggers/functions, indexes/partitioning, performance knobs.
- Identify deltas vs PRD v4; propose minimal DDL deltas to close gaps.

---

### Executive Summary
- Both schemas are strong and production-oriented. v3 is a superset with deeper modeling, performance/partitioning coverage, and integration scope. It aligns more closely with PRD v4 across observability, analytics richness, and Salesforce integration readiness.
- v2 is simpler and still robust; it includes pg_cron scheduling, more concise design, and clear analytics materialized views. It lacks breadth compared to v3 in important areas (multi-embedding support, conversation/AI observability, integration schema, extended content types).
- Recommendation: Adopt `database schema v3.sql` as the baseline. Backport a few v2 strengths (e.g., analytics periodic refresh cadence if pg_cron is enabled) and add small v4-driven tables for proactive intelligence and compliance control states (see “Gaps vs PRD v4” with suggested DDL).

---

### Side-by-Side Comparison

#### Schemas and Extensions
- v2: `core`, `ai`, `analytics`, `audit`, `cache`; extensions include uuid, pgcrypto, pg_trgm, btree_gin, pg_stat_statements, hstore, pg_cron, postgres_fdw, pgvector (as “vector”). Default search path set.
- v3: Adds `integration` schema; includes more tuned DB-level settings section and optional advanced extensions (timescaledb, pg_partman). Search path includes `integration`.
- Verdict: v3 better separation of concerns and forward-compatible for integrations. Matches PRD v4 integration breadth.

#### Types/Domains
- v2: Solid enums for statuses, channels, priority, sentiment; domains for email/url/percentage.
- v3: Richer enums (conversation status includes initialized/processing/transferred; message content types; emotion labels; AI provider/model type). Adds more domains (phone, confidence_score, non_negative_integer) improving data integrity.
- Verdict: v3 aligns with PRD v4’s richer messaging, AI observability, and state machine semantics.

#### Core Tables (Organizations, Users, Conversations, Messages)
- Organizations:
  - v2: Baseline multi-tenant, feature toggles, limits, SF fields.
  - v3: Adds slug, detailed subscription lifecycle/status, branding, localization, stricter constraints, richer feature flags and security policy fields. Current usage counters with triggers.
  - Verdict: v3 superior for tenant governance and feature gating per PRD v4.

- Users:
  - v2: Good baseline (MFA fields, SF IDs, preferences, rate limits).
  - v3: Extensive profile/contact/engagement/API usage/segmentation/consent, RBAC hints, analytics fields (lifetime_value, risk_score), SF objects coverage, device/session tracking.
  - Verdict: v3 aligns with PRD v4 analytics and operational visibility.

- Conversations:
  - v2: Covers counts, sentiment, escalation, AI metrics, CSAT; relational basics; indexes; validity checks.
  - v3: Significantly extended: assignment/routing, detailed time metrics, AI metrics (confidence min/max, retry/fallback counts), sentiment and emotion full history, intent tracking, transfers, CSAT/NPS/CES, categorization, extensive JSONB fields, numerous high-value indexes, composite/activity indexes, and constraints.
  - Verdict: v3 maps tightly to PRD v4 KPIs, state machine, and SLA/operations analytics.

- Messages (partitioned):
  - v2: Monthly partitions; AI analysis fields; moderation basics; basic FTS and entity GIN; attachments; threading; intent/sentiment; performance indexes.
  - v3: Much richer: message_number, multiple content representations (html/markdown/json), translation fields, intent/NER structures, emotion, moderation workflow, edit and soft-delete lifecycle, delivery/read tracking, interactive elements (quick replies/cards), AI usage metadata (provider, model, cost, tokens, latency), comprehensive indexing strategy (GIN for content and metadata, trgm for content, multiple specialized indexes).
  - Verdict: v3 far better for observability, moderation, multilingual, message lifecycle—meeting PRD v4’s AI observability and UX depth.

#### AI/RAG
- Knowledge entries:
  - v2: Solid RAG table: title/content/summary, keywords, search_vector trigger, embedding (1536), quality/usage metrics, indexes for vector and FTS.
  - v3: Adds content hashing, multi-embedding sizes (1536/768/1024), quality/effectiveness metrics (resolution_rate, escalation prevention), publication workflow (draft/review/approved/published), access control, richer categorization/concepts/entities, search tuning (rank/boost), extensive indexes.
  - Verdict: v3 aligns with PRD v4 advanced KB governance and performance.

- Model interactions (AI observability):
  - v2: Tracks model_name/provider, tokens, cost, latency, confidence, errors, retries, metadata; indexes.
  - v3: Extends to include request/response ids, model type, endpoint, chat messages array, more performance metrics (TTFT, tokens/sec), caching flags/keys, HTTP headers, retry linkage.
  - Verdict: v3 superior for cost/compliance/observability; ideal for PRD v4’s AI KPIs and guardrails.

#### Analytics
- v2: `analytics.conversation_metrics` materialized view with deflection-like measures and time aggregations; also `analytics.intent_patterns` table; refresh job via pg_cron.
- v3: Enriched `analytics.conversation_metrics` (resolution/ai coverage/escalation rates, distribution metrics, more dimensions); monitoring views for table size, index usage, slow queries.
- Verdict: v3 broader analytics; backport v2’s scheduled refresh if pg_cron is deployed.

#### Audit
- v2: `audit.activity_log` partitioned with actor/action/resource details and request context; indexes.
- v3: More fields (impersonated_by, service_account, change fields, correlation_id, duration_ms, tags), more partitions created; extensive indexes.
- Verdict: v3 better for PRD v4 compliance and SRE tracing.

#### Integration
- v2: None as separate schema (SF fields embedded per table).
- v3: Dedicated `integration.salesforce_sync` with unique constraints, status, error counts, direction, field mappings, scheduling fields; indexes.
- Verdict: v3 aligns with PRD v4 multi-cloud orchestration and data sync auditability.

#### Cache
- v2: `cache.query_results` with expires, hits, basic fields.
- v3: Adds query_duration, compression, size, retrieval latency, stale flag, richer metadata; more indexes.
- Verdict: v3 better operational insight.

#### RLS, Roles, Permissions
- v2: RLS on users/conversations/messages/knowledge; policies using `app.current_org_id`; roles and grants; default grants.
- v3: Extends RLS to `ai.model_interactions`; defensive `COALESCE(current_setting(...))` in policies; full grant coverage across more schemas; default privileges and function grants; schema-level comments.
- Verdict: v3 safer, broader isolation, aligns better with PRD v4’s multi-tenant and compliance posture.

#### Triggers/Functions and Partitioning
- v2: `update_updated_at`, monthly partition creators (pg_cron), update conversation metrics on message insert; MV refreshers; cleanup of inactive conversations; conversation stats function.
- v3: Universal `update_updated_at` applied via DO block across schemas, richer conversation metrics trigger (including emotion trajectory), monthly partition creation for messages/audit, cleanup procedures (cache cleanup, monthly counters), analytics refresh, usage tracking triggers.
- Verdict: v3 more comprehensive, but v2’s explicit cron schedules can be ported.

#### Performance and Ops Knobs
- v2: Baseline; indexes and pg_cron in use.
- v3: Extensive DB parameter tuning guidance, autovacuum tuning per key tables, monitoring views, and partition defaults.
- Verdict: v3 aligns with PRD v4 SRE/ops excellence.

---

### Alignment to PRD v4

- Multi-tenancy, security, compliance:
  - v3: Strong RLS coverage, audit expansion, roles, and data governance → aligned.
  - v2: Aligned but less complete.

- Conversation intelligence, KPIs, SLA/operations:
  - v3: Rich time metrics, emotion trajectory, intent, transfer/escalations, SLA-ready fields, heavy indexing → fully aligned.
  - v2: Aligned at base level.

- AI observability and guardrails:
  - v3: Detailed `ai.model_interactions`, message-level AI metrics, cost/tokens, retries, cache flags → strong alignment.
  - v2: Good, but fewer fields.

- Knowledge/RAG:
  - v3: Publication workflow, multiple embedding vectors, more search controls and quality metrics → superior alignment.
  - v2: Solid baseline.

- Integrations:
  - v3: Dedicated `integration.salesforce_sync` with strong constraints and indexing → matches PRD v4 cross-cloud orchestration.
  - v2: Lacks this module.

- Analytics/BI:
  - v3: Richer conversation metrics, monitoring views → better alignment.

- Ops/Performance:
  - v3: Partitioning, tuning, autovacuum settings; monitoring views → better aligned with SRE guidance in PRD v4.

Conclusion: v3 meets PRD v4 most closely across nearly every dimension.

---

### Notable Gaps vs PRD v4 (and Suggested DDL Additions)

- Proactive Intelligence (governor limits/org health):
  - Gap: No explicit tables to store predictions and actions.
  - Add:
    - `ai.proactive_predictions(id, organization_id, type, signal_source, predicted_at, prediction_window, risk_score, confidence, recommended_action, remediation_level, status, created_at)`
    - `ai.org_health_snapshots(id, organization_id, health_score, metrics jsonb, detected_patterns jsonb, created_at)`
    - `ai.proactive_actions(id, organization_id, prediction_id, action_type, params jsonb, is_safe boolean, executed_at, success boolean, error_message, created_at)`

- Compliance modules state:
  - Gap: No persistent store for per-tenant compliance checks/violations.
  - Add:
    - `audit.compliance_checks(id, organization_id, module, operation, data_ref, result, violations jsonb, can_remediate boolean, created_at)`
    - `audit.compliance_audit_log(id, organization_id, module, action, actor, details jsonb, created_at)`

- Error budgets and SRE policy tracking (DB optional):
  - If desired:
    - `analytics.error_budget_burn(id, organization_id, window_start, window_end, target, actual, burn_rate, created_at)`

- Scheduled refresh:
  - v3 has procedures but pg_cron commented. If using pg_cron:
    - Schedule `analytics.refresh_views()` and partition creation as in v2.

---

### Risks and Mitigations

- Schema complexity and performance:
  - v3’s breadth may increase migration and ops burden. Leverage feature flags to phase adoption; monitor via `monitoring.*` views; progressive index enablement.

- Vector indices cost:
  - Ensure appropriate lists parameter tuning and dimension alignment with embedding models; avoid unused alternative embeddings if not needed initially.

- RLS correctness:
  - v3’s `COALESCE(current_setting(...))` improves safety. Enforce `SET app.current_org_id` in application layer.

---

### Final Recommendation
- **Adopt `database schema v3.sql` as the primary baseline** for deployment. It better fulfills PRD v4 requirements across multi-tenancy, AI observability, analytics, Salesforce integration, and operational readiness.
- **Backport from v2**:
  - pg_cron scheduling examples for MV refresh and partition creation, if `pg_cron` is available in your environment.
- **Add the proposed PRD v4 deltas**:
  - Proactive intelligence tables (`ai.proactive_*`, `ai.org_health_snapshots`).
  - Compliance check/audit tables (`audit.compliance_checks`, `audit.compliance_audit_log`).
  - Optional error budget tracking (`analytics.error_budget_burn`).

This hybrid delivers a schema that is production-grade, Salesforce-native, measurable against KPIs, and extensible for proactive intelligence and compliance governance as mandated by PRD v4.
