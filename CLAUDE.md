# CLAUDE.md - AI Customer Service Agent for Salesforce

## Project Overview

### Mission
Deliver an enterprise-grade, Salesforce-native AI Customer Service Agent that autonomously resolves ≥85% of support interactions with sub-500ms P99 response time and 99.99% uptime, while improving CSAT to ≥4.5 through emotion-aware, context-rich assistance.

### Business Impact
- **93% reduction** in ticket resolution time (45 min → 3 min)
- **89% improvement** in first contact resolution (45% → 85%) 
- **97% cost reduction** per ticket ($15.00 → $0.50)
- **41% improvement** in customer satisfaction (3.2 → 4.5/5.0)
- **300% increase** in agent productivity (50 → 200/day)
- **$8-12.5M annual savings** with ≥150% ROI in Year 1

## Current Project Status

### ✅ Phase 5 Complete: AI/ML Services Foundation
**AI/ML Core (100% Implemented):**
- Multi-provider LLM support (OpenAI GPT-4, Anthropic Claude, local models)
- Complete NLP pipeline: intent classification, sentiment analysis, emotion detection, entity extraction
- RAG system with vector search (Pinecone), full-text search (Elasticsearch), graph relationships (Neo4j)
- Model routing with fallback chains and cost tracking
- Confidence thresholds and human-in-the-loop integration

### 🔄 Next Priority Phases
**Phase 6: Conversation Engine** (In Progress)
- State machine implementation for conversation lifecycle
- Emotion-aware response generation and tone adjustment
- Context preservation and multi-turn conversation management

**Phase 7: Integrations** (Ready to Start)
- Salesforce Service Cloud and Omni-Channel integration
- Multi-channel support (Web, Mobile, Email, Slack, Teams, API)
- Bi-directional sync with external systems (Jira, Zendesk, etc.)

## Technology Stack

### Core Infrastructure
```yaml
Backend:
  Language: Python 3.11.6
  Framework: FastAPI 0.104.1 (async-first)
  Runtime: uvloop 0.19.0
  Process Manager: gunicorn 21.2.0

AI/ML:
  Primary LLM: OpenAI GPT-4 Turbo
  Secondary LLM: Anthropic Claude-3-Sonnet
  NLP: microsoft/deberta-v3-base, spaCy 3.7.2
  Embeddings: OpenAI text-embedding-3-large (3072 dims)

Databases:
  Primary: PostgreSQL 16.1 + pgvector + pg_trgm
  Cache: Redis 7.2.3
  Vector: Pinecone (serverless, cosine, 3072 dims)
  Search: Elasticsearch 8.11.3
  Graph: Neo4j 5.15.0
  Session: MongoDB 7.0.5

Infrastructure:
  Container: Docker 24
  Orchestration: Kubernetes 1.29.0
  Service Mesh: Istio 1.20.1
  API Gateway: Kong 3.5.0
  Message Queue: Kafka 3.6.1 (Avro)
  Tasks: Celery 5.3.4 (Redis backend)
```

## Critical Success Criteria

### Technical KPIs (Non-Negotiable)
- **Latency**: P99 ≤500ms (target ≤300ms steady state)
- **Availability**: 99.99% uptime
- **Throughput**: 1,000 RPS capacity
- **Error Rate**: ≤0.1%
- **Cache Hit Ratio**: ≥90%

### Business KPIs
- **Deflection Rate**: ≥85% automated resolution
- **First Contact Resolution**: ≥80%
- **Cost per Interaction**: ≤$0.50
- **Customer Satisfaction**: ≥4.5/5.0
- **ROI**: ≥150% within 6-9 months

### AI Performance Metrics
- **Intent Accuracy**: ≥92%
- **Average Confidence**: ≥0.85
- **Fallback Rate**: ≤5%
- **Model Response Time**: <100ms for classification

## Architecture Patterns

### Design Principles
1. **Contract-First Development**: OpenAPI specs before implementation
2. **Type Safety**: Full Python 3.11+ type hints, MyPy strict mode
3. **Async-First**: No blocking I/O in request paths
4. **Multi-Tenancy**: Row-level security with organization isolation
5. **Observability-by-Design**: Correlation IDs, metrics, traces throughout
6. **Security-by-Design**: Zero-trust architecture, field-level encryption

### Key Architectural Components

#### AI Orchestration Engine
```python
class AIOrchestrationEngine:
    """Central AI coordination with fallback chains and guardrails"""
    
    def __init__(self):
        self.model_router = ModelRouter()           # Smart model selection
        self.guardrails = SafetyGuardrails()        # Content filtering
        self.sf_native = SalesforceNativeLayer()    # Apex/SOQL tooling
        self.fallbacks = FallbackChain()           # Resilience patterns
        self.context = ConversationContextStore()   # State management
        self.error_recovery = ErrorRecovery()       # Fault tolerance
```

#### Multi-Database Strategy
- **PostgreSQL**: Core transactional data with pgvector for embeddings
- **Redis**: Session management, rate limiting, feature flags
- **Pinecone**: High-performance vector search for RAG
- **Elasticsearch**: Full-text search and analytics
- **Neo4j**: Relationship mapping and knowledge graphs

#### Data Model Highlights
- **Partitioned Tables**: Messages and audit logs by date
- **RLS Enforcement**: Organization isolation at database level
- **Comprehensive Analytics**: Materialized views for real-time metrics
- **Audit Trail**: Complete activity logging with change tracking

## Development Standards

### Code Quality Requirements
```yaml
Formatting: Black (line-length: 100)
Linting: Ruff with security rules
Type Checking: MyPy strict mode enabled
Testing: 
  - Unit coverage ≥85%
  - Integration with testcontainers
  - E2E with Playwright
  - Performance with Locust
  - Security: SAST/DAST scanning
```

### Security Standards
- **Authentication**: JWT/OIDC with MFA for admins
- **Encryption**: AES-256-GCM at rest, TLS 1.3 in transit
- **Secrets Management**: HashiCorp Vault integration
- **Compliance Modules**: HIPAA/PCI/FedRAMP/GDPR as tenant-configurable packs
- **Zero-Trust**: Device posture, network reputation, continuous authorization

### API Standards
- **OpenAPI 3.0**: Complete specification with examples
- **RESTful Design**: Consistent resource naming and operations
- **WebSocket**: Real-time communication for chat interfaces
- **Rate Limiting**: Per-organization and per-user quotas
- **Error Handling**: Standardized error responses with correlation IDs

## Implementation Roadmap

### Immediate Focus (Next 2 Weeks)
1. **Complete Phase 6**: Conversation engine with emotion-aware responses
2. **Start Phase 7**: Salesforce Service Cloud integration
3. **Add Dependencies**: Missing AI/ML packages to pyproject.toml
4. **Integration Testing**: Connect AI services with infrastructure

### Short-term Goals (1 Month)
1. **Frontend Development**: React + TypeScript chat interface
2. **Multi-channel Support**: Email, Slack, Teams integrations
3. **Testing Suite**: Achieve 85% test coverage across all components
4. **Performance Optimization**: Database indexing and query optimization

### Long-term Objectives (3 Months)
1. **Production Deployment**: Kubernetes with full observability
2. **Advanced AI Features**: Salesforce-specific model fine-tuning
3. **Compliance Certification**: Industry module implementations
4. **Scale Testing**: 50,000 concurrent user validation

## Key Dependencies and Constraints

### External Dependencies
- **OpenAI API**: Primary LLM provider (configure rate limits and fallbacks)
- **Salesforce APIs**: Metadata API, Bulk API, Streaming API
- **Cloud Infrastructure**: Multi-region Kubernetes deployment
- **Monitoring Stack**: Prometheus, Grafana, Jaeger, PagerDuty

### Technical Constraints
- **Async-Only**: No blocking operations in request paths
- **Multi-tenant**: Organization isolation mandatory for all operations
- **Compliance**: Industry-specific requirements (HIPAA, PCI, FedRAMP)
- **Performance**: Sub-500ms response times at scale

## Common Development Patterns

### Service Implementation Pattern
```python
# src/services/base.py
class BaseService:
    """Base service with logging, metrics, and error handling"""
    
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
                self.logger.error(f"Operation failed: {operation}", error=e)
                self.metrics.increment(f"service.{operation}.error")
                raise
```

### Repository Pattern
```python
# src/repositories/base.py
class BaseRepository:
    """Base repository with RLS and connection management"""
    
    def __init__(self, session: AsyncSession, organization_id: UUID):
        self.session = session
        self.org_id = organization_id
        
    async def set_org_context(self):
        """Set organization context for RLS"""
        await self.session.execute(
            text("SET app.current_org_id = :org_id"),
            {"org_id": str(self.org_id)}
        )
```

### AI Service Integration
```python
# src/services/ai/orchestrator.py
class AIOrchestrator:
    """Route requests to appropriate models with fallbacks"""
    
    async def process_message(self, message: str, context: Context) -> AIResponse:
        # Route based on message type and context
        model = self.model_router.select(message, context)
        
        # Apply guardrails and safety checks
        if not self.guardrails.validate(message):
            return AIResponse.safe_fallback()
            
        # Generate with fallback chain
        try:
            response = await model.generate(message, context)
        except ModelError:
            response = await self.fallbacks.get_next_model().generate(message, context)
            
        # Track costs and confidence
        self.track_metrics(response)
        return response
```

## Testing Strategy

### Test Categories
1. **Unit Tests**: Individual component testing with mocks
2. **Integration Tests**: Database and external service testing
3. **E2E Tests**: Complete user journey testing
4. **Performance Tests**: Load testing with Locust (1000 RPS target)
5. **Security Tests**: SAST/DAST scanning and penetration testing
6. **Chaos Tests**: Failure injection and resilience validation

### Test Data Management
- **Factories**: Pydantic-based test data generation
- **Fixtures**: Reusable test setup and teardown
- **Mock Services**: External service simulation
- **Test Containers**: Real database instances for integration tests

## Monitoring and Observability

### Key Metrics
- **Application**: Request latency, error rates, throughput
- **AI Performance**: Model accuracy, confidence scores, cost tracking
- **Business**: Deflection rates, CSAT scores, resolution times
- **Infrastructure**: CPU/memory usage, database connections, cache hit rates

### Alerting Rules
```yaml
alerts:
  - name: HighErrorRate
    expr: rate(errors_total[5m]) > 0.01
    severity: critical
    
  - name: HighLatencyP99
    expr: histogram_quantile(0.99, rate(api_request_duration_seconds_bucket[5m])) > 0.5
    severity: warning
    
  - name: HighFallbackRate
    expr: rate(ai_fallback_triggered_total[5m]) > 0.1
    severity: critical
```

## Error Handling and Recovery

### Error Categories
1. **Validation Errors**: Invalid input, schema violations
2. **Business Errors**: Rule violations, permission denied
3. **System Errors**: Database connection, external service failures
4. **AI Errors**: Model timeouts, low confidence, hallucination detection

### Recovery Strategies
- **Circuit Breakers**: Prevent cascade failures
- **Retry Logic**: Exponential backoff with jitter
- **Fallback Chains**: Alternative models and services
- **Graceful Degradation**: Reduced functionality vs complete failure

## Security Considerations

### Data Protection
- **Encryption at Rest**: AES-256-GCM for sensitive fields
- **Encryption in Transit**: TLS 1.3 minimum
- **PII Tokenization**: Replace sensitive data with tokens
- **Field-Level Security**: Granular access controls

### Access Control
- **RBAC**: Role-based permissions with inheritance
- **API Rate Limiting**: Per-organization and per-user quotas
- **JWT Validation**: Signature verification and expiration checks
- **Audit Logging**: Complete access and change tracking

## Performance Optimization

### Database Optimization
- **Connection Pooling**: Async connection management
- **Query Optimization**: Index design and query analysis
- **Caching Strategy**: Multi-level caching (Redis, application, CDN)
- **Partitioning**: Time-based partitioning for high-volume tables

### AI Optimization
- **Model Caching**: Cache frequently used model responses
- **Batch Processing**: Group similar requests for efficiency
- **Streaming**: Progressive response generation for UX
- **Cost Management**: Token usage tracking and optimization

## Development Workflow

### Local Development
```bash
# Setup
make install          # Install dependencies
make dev-setup       # Setup development environment

# Development
make run             # Start development server
make test            # Run tests
make test-cov        # Run tests with coverage
make lint            # Run linting and formatting
make security        # Run security scans

# Database
make db-migrate      # Run database migrations
make db-seed         # Seed database with test data
```

### Git Workflow
1. Feature branches from `main`
2. PR reviews required with CI checks
3. Semantic commit messages
4. Automated testing and security scanning
5. Staging deployment before production

## Common Issues and Solutions

### Database Issues
- **Connection Pool Exhaustion**: Monitor pool metrics and adjust limits
- **Slow Queries**: Use pg_stat_statements for analysis
- **Lock Contention**: Optimize transaction scope and isolation levels

### AI Service Issues
- **Model Timeouts**: Implement circuit breakers and fallbacks
- **Rate Limiting**: Monitor usage and implement backoff strategies
- **Low Confidence**: Route to human agents or request clarification

### Integration Issues
- **Salesforce API Limits**: Implement quota management and retries
- **Webhook Failures**: Use dead letter queues and retry mechanisms
- **Sync Conflicts**: Implement conflict resolution strategies

## Compliance and Governance

### Model Governance
- **Version Control**: Track model versions and performance
- **A/B Testing**: Validate model updates before full deployment
- **Rollback Strategy**: Quick reversion for problematic updates
- **Bias Testing**: Regular fairness and bias assessments

### Data Governance
- **Retention Policies**: Automated data lifecycle management
- **Privacy Controls**: GDPR/CCPA compliance with data subject rights
- **Audit Requirements**: Comprehensive logging and reporting
- **Industry Compliance**: HIPAA, PCI-DSS, FedRAMP modules

## Next Steps for Development

### Immediate Actions
1. Review current Phase 5 implementation for any gaps
2. Begin Phase 6 conversation engine development
3. Set up Salesforce development environment
4. Implement missing dependencies in pyproject.toml

### Short-term Goals
1. Complete conversation state machine
2. Integrate emotion-aware response generation
3. Start Salesforce Service Cloud connector
4. Implement multi-channel message handling

### Long-term Objectives
1. Achieve 85% deflection rate target
2. Optimize for sub-300ms response times
3. Implement advanced AI features (proactive intelligence)
4. Complete compliance module certifications

---

*This CLAUDE.md file provides comprehensive guidance for AI coding agents working on the AI Customer Service Agent for Salesforce project. It represents the current state and planned implementation based on PRD v4, Solution Blueprint v4, and the Coding Execution Plan v3.*