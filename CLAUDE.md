# CLAUDE.md - AI Customer Service Agent for Salesforce

## Project Mission & Core Objectives

**Primary Mission**: Deliver an enterprise-grade, Salesforce-native AI Customer Service Agent that autonomously resolves ≥85% of support interactions with sub-500ms P99 response time and 99.99% uptime, while improving CSAT to ≥4.5 through emotion-aware, context-rich assistance.

**Business Value Targets** (PRD v4 Section 1.2):
- Ticket Resolution Time: 45 min → 3 min (-93%)
- First Contact Resolution: 45% → 85% (+89%)
- Support Cost per Ticket: $15.00 → $0.50 (-97%)
- Customer Satisfaction: 3.2/5 → 4.5/5 (+41%)
- Agent Productivity: 50/day → 200/day (+300%)
- Annual Cost Savings: $8-12.5M
- ROI (Year 1): ≥150%

**Success Criteria** (PRD v4 Section 1.3):
- ≥85% automated deflection within 9 months
- P99 latency ≤500ms (steady-state goal ≤300ms)
- Uptime ≥99.99% within 3 months of GA
- CSAT ≥4.5/5.0 sustained
- Positive ROI within 6-9 months

## Current Implementation Status

### ✅ Phase 5 Complete: AI/ML Services (16/16 files implemented)
**Core AI Infrastructure Operational:**
- Multi-provider LLM support (OpenAI GPT-4, Anthropic Claude, local CodeLlama)
- Complete NLP pipeline: intent classification, sentiment analysis, emotion detection, entity extraction
- RAG system with unified retrieval (Pinecone vector + Elasticsearch FTS + Neo4j graph)
- Model routing with fallback chains and cost tracking
- Confidence thresholds and human-in-the-loop integration

### 🔄 Next Critical Phases
**Phase 6: Conversation Engine** (6 days) - IN PROGRESS
- State machine: initialization → context-gathering → processing → solution → confirmation → resolved/escalation
- Emotion-aware response generation with tone adjustment
- Context preservation and multi-turn conversation management

**Phase 7: Integrations** (6 days) - READY TO START
- Salesforce Service Cloud integration with Omni-Channel support
- Multi-channel support: Web, Mobile, Email, Slack, Teams, API
- Bi-directional sync with external systems (Jira, ServiceNow, Zendesk)

## Technology Stack (PRD v4 Section 4)

### Core Backend
```yaml
Language: Python 3.11.6
Framework: FastAPI 0.104.1 (async-first)
Runtime: uvloop 0.19.0
Process Manager: gunicorn 21.2.0
```

### AI/ML Stack
```yaml
Primary LLM: OpenAI GPT-4 Turbo (gpt-4-1106-preview)
Secondary LLM: Anthropic Claude-3-Sonnet
Local Fallback: CodeLlama-13B (code generation)
NLP Models: microsoft/deberta-v3-base, cardiffnlp/twitter-roberta-base-sentiment
NER: spaCy 3.7.2 (en_core_web_trf)
Embeddings: OpenAI text-embedding-3-large (3072 dimensions)
```

### Data Architecture (PRD v4 + Schema v4)
```yaml
Primary OLTP: PostgreSQL 16.1
  Extensions: pgvector, pg_trgm, uuid-ossp, pgcrypto, pg_stat_statements
Cache: Redis 7.2.3
Vector DB: Pinecone (serverless, cosine, 3072 dims)
Search: Elasticsearch 8.11.3
Graph DB: Neo4j 5.15.0
Session Store: MongoDB 7.0.5
```

### Infrastructure (PRD v4 Section 4)
```yaml
Container: Docker 24
Orchestration: Kubernetes 1.29.0
Service Mesh: Istio 1.20.1
API Gateway: Kong 3.5.0
CDN/WAF/DDoS: CloudFlare
Message Queue: Kafka 3.6.1 (Avro)
Task Queue: Celery 5.3.4 (Redis backend)
```

### Monitoring Stack
```yaml
Metrics: Prometheus + Grafana, Datadog
Logs: ELK Stack (Filebeat → Elasticsearch → Kibana)
Tracing: Jaeger 1.52.0
Alerting: PagerDuty (Opsgenie backup)
```

## Database Schema Compliance (Schema v4.sql)

### Core Schemas
- **core**: organizations, users, conversations, messages, actions, escalations
- **ai**: knowledge_entries, intents, model_performance, learning_feedback
- **analytics**: materialized views (conversation_metrics, intent_metrics)
- **audit**: partitioned activity_log, privacy_log
- **integration**: salesforce_sync, external_connectors
- **cache**: query_results for performance optimization

### Key Features Implemented
- **Row Level Security (RLS)**: Organization isolation via `app.current_org_id`
- **Partitioned Tables**: Messages and audit logs by created_at (monthly)
- **Vector Indexes**: ivfflat indexes for 1536, 768, and 1024 dimension embeddings
- **Composite Indexes**: Optimized for conversation status, channels, priorities
- **Materialized Views**: Real-time analytics with concurrent refresh
- **Audit Partitioning**: Time-based partitioning for high-volume audit data

### Custom Types & Domains
```sql
conversation_status: ENUM with 10 states (initialized → archived)
conversation_channel: ENUM with 13 channels (web_chat → salesforce)
sentiment_label: 5-level scale (very_negative → very_positive)
emotion_label: 7 emotions (angry → excited)
model_provider: 9 providers (openai → custom)
```

## Performance Requirements (PRD v4 Section 7.1)

### API Performance
- **P50 Latency**: <200ms
- **P99 Latency**: <500ms (target <300ms steady state)
- **Throughput**: 1,000 RPS
- **Concurrent Users**: 50,000
- **Database Queries**: <50ms (pg_stat_statements)
- **Cache Hit Ratio**: >90%

### WebSocket Performance
- **Response Time**: <100ms
- **Connection Limit**: 50,000 concurrent
- **Message Delivery**: Guaranteed with retry logic

## Architecture Patterns (Solution Blueprint v4)

### AI Orchestration Engine
```python
class AIOrchestrationEngine:
    def __init__(self):
        self.model_router = ModelRouter()           # Smart model selection
        self.guardrails = SafetyGuardrails()        # Content filtering
        self.sf_native = SalesforceNativeLayer()    # Apex/SOQL tooling
        self.fallbacks = FallbackChain()           # Resilience patterns
        self.context = ConversationContextStore()   # State management
        self.error_recovery = ErrorRecovery()       # Fault tolerance

    async def process(self, req: Request) -> Response:
        ctx = await self.context.load(req.session_id)
        plan = await self.sf_native.plan_if_technical(req, ctx)
        model = self.model_router.select(req, plan, ctx)
        resp = await self.fallbacks.generate_with_validation(model, req, ctx, self.guardrails)
        await self.context.update(ctx, req, resp)
        return resp
```

### Multi-Tenant Isolation
- **Logical Separation**: Organization ID-based RLS at database level
- **Physical Isolation**: Optional for high-compliance tenants
- **Resource Quotas**: Per-tenant compute, API limits, feature flags
- **Data Encryption**: Organization-specific encryption keys

### Security Architecture (Zero-Trust)
- **Authentication**: Auth0 (OAuth2/OIDC) with MFA for admins
- **Authorization**: RBAC with least privilege and JIT access
- **Encryption**: AES-256-GCM at rest, TLS 1.3 in transit
- **Secrets Management**: HashiCorp Vault 1.15.4
- **WAF**: CloudFlare with OWASP CRS

## Development Standards (Coding Plan v3)

### Code Quality
```yaml
Type Safety: Python 3.11+ with full type hints, MyPy strict mode
Formatting: Black (line-length: 100)
Linting: Ruff with security rules (S)
Testing: 
  Unit: pytest with ≥85% coverage
  Integration: testcontainers for real services
  E2E: Playwright for user journeys
  Performance: Locust for 1000 RPS validation
  Security: bandit (SAST), pip-audit (dependencies)
```

### Async Patterns
- **No Blocking I/O**: All database calls and external services async
- **Connection Pooling**: Async SQLAlchemy with proper pool management
- **Circuit Breakers**: Prevent cascade failures in microservices
- **Timeout Management**: Comprehensive timeout configuration

## Critical Implementation Requirements

### Salesforce-Native Features (Phase 11)
- **Apex Analyzer**: Syntax validation, anti-pattern detection, best practices
- **SOQL/SOSL Optimizer**: Governor-limit aware query optimization
- **Code Generation**: Apex/LWC/Flows with test generation
- **Debug Log Analysis**: Automated error diagnosis and resolution
- **Cross-Cloud Orchestration**: Service→Sales→Marketing→Commerce integration

### Proactive Intelligence (Phase 12)
- **Governor Limit Prediction**: ≥70% precision for CPU/API/breach forecasting
- **Org Health Monitoring**: Real-time metrics and anomaly detection
- **Auto-Remediation**: Safe automated fixes for low-risk issues
- **Recommendation Engine**: Context-aware action suggestions

### Compliance Modules (Phase 13)
- **HIPAA**: PHI detection, encryption, audit logging
- **PCI-DSS**: Cardholder data handling, network segmentation
- **FedRAMP**: Boundary control, immutable logs, change control
- **GDPR/CCPA**: Consent management, data subject rights, minimization

## Testing Requirements (PRD v4 Section 11)

### Test Coverage Targets
- **Unit Tests**: ≥85% coverage
- **Integration Tests**: All external service integrations
- **E2E Tests**: Complete user journeys per channel
- **Performance Tests**: 1000 RPS with P99 ≤500ms
- **Security Tests**: SAST (SonarQube/Semgrep), DAST (OWASP ZAP)
- **Chaos Tests**: Cache outage, API rate limit, metadata deploy failure

### Salesforce-Specific Test Scenarios
- Governor limit exhaustion handling
- Debug log analysis accuracy
- Metadata deployment failures
- Bulk API timeout scenarios
- OAuth token revocation
- Multi-org authentication

## Monitoring & Alerting (PRD v4 Section 13)

### Key Metrics
```yaml
API: latency_histograms, request_rates, error_rates
AI: model_latency, confidence_scores, token_usage, costs
Business: deflection_rate, escalation_rate, CSAT, FCR
Infrastructure: cpu_memory, db_connections, cache_hits
```

### Critical Alerts
```yaml
- HighErrorRate: rate(errors_total[5m]) > 0.01
- HighLatencyP99: histogram_quantile(0.99, rate(api_request_duration_seconds_bucket[5m])) > 0.5
- HighFallbackRate: rate(ai_fallback_triggered_total[5m]) > 0.1
- LowCacheHitRatio: cache_hit_ratio < 0.9
- DatabaseConnectionExhaustion: pg_stat_activity_count > 150
```

## Implementation Timeline (Coding Plan v3)

### Current Status
- **Week 1**: Phases 1-2 ✅ (Core Infrastructure, Database)
- **Week 2**: Phases 3-5 ✅ (API Framework, Business Logic, AI/ML)
- **Week 3**: Phases 6-8 (Conversation Engine, Integrations, Frontend)
- **Week 4**: Phase 9 + partial 10 (Testing, DevOps)
- **Week 5**: Phases 10-12 (DevOps, Salesforce Tech, Proactive)
- **Week 6**: Phases 13-14 (Compliance, SRE) + Hardening

### Parallel Execution Strategy
- **Frontend Team**: Can start Phase 8 after Phase 3 completion
- **Integration Team**: Start Phase 7 after Phase 3, parallel with 6
- **DevOps Team**: Phase 10 can run parallel with development phases
- **QA Team**: Phase 9 testing begins as components complete

## Risk Management (PRD v4 Section 17)

### High-Risk Areas
1. **AI Hallucination**: Mitigated via confidence thresholds, KB grounding, citations
2. **Model Drift**: Continuous monitoring with golden datasets and A/B testing
3. **Salesforce Integration**: Complex metadata API interactions, governor limits
4. **Multi-tenant Scale**: Resource isolation and fair usage enforcement
5. **Compliance Audit**: Industry-specific regulatory requirements

### Mitigation Strategies
- **Red-teaming**: Regular adversarial testing of AI responses
- **Chaos Engineering**: Automated failure injection in staging
- **Circuit Breakers**: Prevent cascade failures across services
- **Human-in-the-loop**: Critical decision points with agent review
- **Rollback Plans**: Quick reversion for problematic deployments

## Common Development Patterns

### Service Layer Pattern
```python
# Base service with telemetry and error handling
class BaseService:
    def __init__(self, organization_id: UUID):
        self.org_id = organization_id
        self.logger = get_logger(__name__, organization_id)
        self.metrics = get_metrics_client()
        
    async def execute_with_telemetry(self, operation: str, func: Callable):
        with self.metrics.timer(f"service.{operation}"):
            try:
                result = await func()
                self.metrics.increment(f"service.{operation}.success")
                return result
            except Exception as e:
                self.logger.error(f"Operation failed", operation=operation, error=e)
                self.metrics.increment(f"service.{operation}.error")
                raise
```

### Repository Pattern with RLS
```python
# Base repository with organization context
class BaseRepository:
    def __init__(self, session: AsyncSession, organization_id: UUID):
        self.session = session
        self.org_id = organization_id
        
    async def set_org_context(self):
        await self.session.execute(
            text("SET app.current_org_id = :org_id"),
            {"org_id": str(self.org_id)}
        )
```

### AI Integration Pattern
```python
# Model routing with fallbacks and cost tracking
class AIModelRouter:
    async def generate_response(self, request: AIRequest) -> AIResponse:
        # Select optimal model based on request type and context
        model = self.select_model(request)
        
        # Apply safety guardrails
        if not self.guardrails.validate(request):
            return AIResponse.safe_fallback()
            
        # Generate with fallback chain
        try:
            response = await model.generate(request)
        except ModelError as e:
            # Fallback to secondary model
            response = await self.fallback_model.generate(request)
            
        # Track costs and confidence
        self.track_metrics(response)
        return response
```

## Environment Configuration

### Required Environment Variables
```bash
# Core Configuration
ENVIRONMENT=development|staging|production
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR

# Security
SECURITY__SECRET_KEY=<256-bit-secret>
SECURITY__ENCRYPTION_KEY=<32-byte-hex-key>
SECURITY__HMAC_SECRET=<hmac-secret>

# Database
DATASTORE__DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DATASTORE__REDIS_URL=redis://host:6379/0

# AI Services
OPENAI_API_KEY=<openai-key>
ANTHROPIC_API_KEY=<anthropic-key>
PINECONE_API_KEY=<pinecone-key>
PINECONE_ENVIRONMENT=<pinecone-env>

# Monitoring
DATADOG_API_KEY=<datadog-key>
PAGERDUTY_INTEGRATION_KEY=<pagerduty-key>
```

## Quality Gates and Validation

### Pre-commit Checks
```bash
make lint          # Ruff linting
make format        # Black formatting  
make type-check    # MyPy strict mode
make security      # Bandit + pip-audit
make test          # Unit tests with coverage
```

### Pre-deployment Validation
- ✅ All tests pass (≥85% coverage)
- ✅ Security scans clean (SAST/DAST)
- ✅ Performance benchmarks met (P99 ≤500ms)
- ✅ API documentation updated (OpenAPI 3.0)
- ✅ Database migrations tested (forward/backward)
- ✅ Infrastructure as code validated
- ✅ Monitoring dashboards deployed
- ✅ Runbooks updated and tested

---

**This CLAUDE.md file represents the authoritative development guide for the AI Customer Service Agent project, fully aligned with PRD v4, Solution Blueprint v4, Database Schema v4, and Coding Execution Plan v3.**