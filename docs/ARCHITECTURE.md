# System Architecture

This document provides a comprehensive overview of the Texas PIA Request Automation System architecture, including system design, component interactions, and technical decisions.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Principles](#architecture-principles)
- [System Components](#system-components)
- [Data Flow](#data-flow)
- [Agent Orchestration System](#agent-orchestration-system)
- [Database Schema](#database-schema)
- [Microsoft 365 Integration](#microsoft-365-integration)
- [AI Classification Pipeline](#ai-classification-pipeline)
- [Security Architecture](#security-architecture)
- [Scalability Considerations](#scalability-considerations)

## System Overview

The Texas PIA Request Automation System is a distributed application built on a microservices-inspired architecture with autonomous agents handling specific responsibilities. The system processes Public Information Act requests through automated document retrieval, machine learning classification, and workflow management.

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                             │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │           React Frontend (TypeScript)                    │     │
│  │  - Dashboard UI         - Document Viewer               │     │
│  │  - Request Management   - Classification Review         │     │
│  │  - Workflow Interface   - Admin Panel                   │     │
│  └─────────────────────────────────────────────────────────┘     │
└────────────────────────────┬──────────────────────────────────────┘
                             │ HTTPS / REST API
┌────────────────────────────┴──────────────────────────────────────┐
│                      Application Layer                             │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │              FastAPI Backend (Python)                    │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │     │
│  │  │   Auth   │ │ Requests │ │Documents │ │ Workflow  │ │     │
│  │  │    API   │ │   API    │ │   API    │ │    API    │ │     │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘ │     │
│  │                                                          │     │
│  │  ┌────────────────────────────────────────────────────┐ │     │
│  │  │           Service Layer                             │ │     │
│  │  │  - Document Processing  - AI Classification        │ │     │
│  │  │  - Email Deduplication  - Workflow Engine          │ │     │
│  │  │  - Deadline Management  - Microsoft Graph Client   │ │     │
│  │  └────────────────────────────────────────────────────┘ │     │
│  └─────────────────────────────────────────────────────────┘     │
└────────────────────────────┬──────────────────────────────────────┘
                             │
┌────────────────────────────┴──────────────────────────────────────┐
│                      Processing Layer                              │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │         Celery Workers (Background Tasks)                │     │
│  │  - Document retrieval     - Text extraction             │     │
│  │  - Email processing       - Batch classification        │     │
│  │  - Report generation      - Notifications               │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │           Agent Orchestrator                             │     │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │     │
│  │  │  Request     │ │  Document    │ │  Email         │  │     │
│  │  │  Monitor     │ │  Retrieval   │ │  Retrieval     │  │     │
│  │  └──────────────┘ └──────────────┘ └────────────────┘  │     │
│  │  ┌──────────────┐ ┌──────────────┐                     │     │
│  │  │Classification│ │  Deadline    │                     │     │
│  │  │    Agent     │ │  Monitor     │                     │     │
│  │  └──────────────┘ └──────────────┘                     │     │
│  │                                                          │     │
│  │         Event Bus (Redis Pub/Sub)                       │     │
│  └─────────────────────────────────────────────────────────┘     │
└────────────────────────────┬──────────────────────────────────────┘
                             │
┌────────────────────────────┴──────────────────────────────────────┐
│                       Data Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  PostgreSQL  │  │    Redis     │  │ Azure Blob   │           │
│  │              │  │              │  │   Storage    │           │
│  │  - Requests  │  │  - Cache     │  │  - Documents │           │
│  │  - Documents │  │  - Sessions  │  │  - Files     │           │
│  │  - Workflow  │  │  - Queue     │  │              │           │
│  │  - Audit Log │  │              │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────────────────────┬──────────────────────────────────────┘
                             │
┌────────────────────────────┴──────────────────────────────────────┐
│                    External Services                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Microsoft  │  │   OpenAI     │  │    SMTP      │           │
│  │  Graph API   │  │   GPT-4      │  │   Server     │           │
│  │              │  │              │  │              │           │
│  │ - SharePoint │  │ - Document   │  │ - Email      │           │
│  │ - OneDrive   │  │   Classification│ │  Notifications│         │
│  │ - Outlook    │  │              │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└───────────────────────────────────────────────────────────────────┘
```

## Architecture Principles

### 1. Separation of Concerns
- **Presentation Layer**: React frontend focused solely on UI/UX
- **Application Layer**: FastAPI backend handles business logic
- **Processing Layer**: Celery workers and agents handle async operations
- **Data Layer**: PostgreSQL for relational data, Redis for caching/queuing

### 2. Event-Driven Architecture
- Agents communicate via publish-subscribe event bus
- Loose coupling between system components
- Asynchronous processing for long-running tasks
- Real-time updates through event propagation

### 3. Agent-Based Design
- Autonomous agents with specific responsibilities
- Self-healing with automatic restart capabilities
- Health monitoring and status reporting
- Scalable through agent replication

### 4. API-First Development
- RESTful API design with OpenAPI documentation
- Versioned API endpoints (/api/v1)
- Comprehensive request/response schemas
- Clear error handling and status codes

### 5. Security by Design
- JWT-based authentication
- Role-based access control (RBAC)
- Audit logging for all operations
- Encrypted data transmission (HTTPS/TLS)

## System Components

### Backend Services

#### FastAPI Application (`app/main.py`)
- Entry point for the REST API
- CORS configuration for frontend integration
- OpenAPI documentation generation
- Health check endpoints
- Lifecycle management (startup/shutdown)

#### Database Layer (`app/core/database.py`)
- SQLAlchemy 2.0 async engine
- Connection pooling
- Automatic session management
- Migration support via Alembic

#### Authentication Service (`app/core/security.py`)
- JWT token generation and validation
- Password hashing with bcrypt
- Token refresh mechanism
- User session management

#### Request Management (`app/api/routes/requests.py`)
- CRUD operations for PIA requests
- Deadline calculation and tracking
- Extension request handling
- AG ruling workflow initiation

#### Document Management (`app/api/routes/documents.py`)
- Document upload and storage
- Classification management
- Redaction tracking
- Download endpoints

### Agent System

#### Agent Orchestrator (`app/services/agents/orchestrator.py`)
The master coordinator managing all autonomous agents:

```
┌────────────────────────────────────────────────┐
│         Agent Orchestrator                      │
│                                                 │
│  ┌──────────────────────────────────────┐     │
│  │     Lifecycle Management              │     │
│  │  - Start/Stop agents                  │     │
│  │  - Health monitoring                  │     │
│  │  - Automatic restart on failure       │     │
│  │  - Graceful shutdown                  │     │
│  └──────────────────────────────────────┘     │
│                                                 │
│  ┌──────────────────────────────────────┐     │
│  │     Event Bus Integration             │     │
│  │  - Subscribe to system events         │     │
│  │  - Publish orchestrator events        │     │
│  │  - Inter-agent communication          │     │
│  └──────────────────────────────────────┘     │
│                                                 │
│  ┌──────────────────────────────────────┐     │
│  │     Agent Registry                    │     │
│  │  - Request Monitor                    │     │
│  │  - Document Retrieval                 │     │
│  │  - Email Retrieval                    │     │
│  │  - Classification Agent               │     │
│  │  - Deadline Monitor                   │     │
│  └──────────────────────────────────────┘     │
└────────────────────────────────────────────────┘
```

#### Base Agent (`app/services/agents/base_agent.py`)
Abstract base class providing:
- State management (IDLE, RUNNING, PAUSED, ERROR)
- Event bus integration
- Health check mechanism
- Graceful shutdown handling
- Error recovery

#### Request Monitor Agent
- Polls for new PIA requests
- Initiates workflow creation
- Triggers initial document retrieval
- Publishes REQUEST_CREATED events

#### Document Retrieval Agent
- Retrieves documents from SharePoint/OneDrive
- Applies search filters and date ranges
- Downloads files to storage
- Publishes DOCUMENTS_RETRIEVED events

#### Email Retrieval Agent
- Searches Outlook mailboxes
- Retrieves email threads
- Extracts attachments
- Performs thread grouping
- Publishes EMAILS_RETRIEVED events

#### Classification Agent
- Monitors for unclassified documents
- Batches documents for AI classification
- Rate-limits API calls to GPT-4
- Updates document classifications
- Publishes CLASSIFICATION_COMPLETE events

#### Deadline Monitor Agent
- Monitors approaching deadlines
- Sends alerts at 7, 3, and 1 day thresholds
- Identifies overdue requests
- Publishes DEADLINE_ALERT events

### Event Bus System

Event-driven communication backbone:

```
┌────────────────────────────────────────────────────────┐
│                 Event Bus (Redis Pub/Sub)              │
│                                                         │
│  Event Types:                                          │
│  ┌──────────────────────────────────────────────┐    │
│  │ REQUEST_CREATED                               │    │
│  │ DOCUMENTS_RETRIEVED                           │    │
│  │ EMAILS_RETRIEVED                              │    │
│  │ CLASSIFICATION_COMPLETE                       │    │
│  │ WORKFLOW_TASK_COMPLETE                        │    │
│  │ DEADLINE_ALERT                                │    │
│  │ AG_SUBMISSION_REQUIRED                        │    │
│  │ AGENT_HEARTBEAT                               │    │
│  │ ERROR / AGENT_ERROR                           │    │
│  └──────────────────────────────────────────────┘    │
│                                                         │
│  Subscribers:                                          │
│  - All Agents                                          │
│  - Orchestrator                                        │
│  - Workflow Engine                                     │
│  - WebSocket Handler (for real-time UI updates)       │
└────────────────────────────────────────────────────────┘
```

## Data Flow

### Request Processing Flow

```
1. Request Created
   │
   ├─> Request Monitor Agent detects new request
   │   │
   │   └─> Publishes REQUEST_CREATED event
   │
   ├─> Workflow Engine creates task workflow
   │   │
   │   └─> Tasks: Retrieval → Classification → Review → Approval
   │
2. Document Retrieval Phase
   │
   ├─> Document Retrieval Agent subscribes to REQUEST_CREATED
   │   │
   │   ├─> Connects to SharePoint via Graph API
   │   ├─> Applies search filters (keywords, dates, departments)
   │   ├─> Downloads matching documents
   │   ├─> Calculates SHA-256 hashes
   │   └─> Saves to database and storage
   │
   ├─> Email Retrieval Agent subscribes to REQUEST_CREATED
   │   │
   │   ├─> Connects to Outlook via Graph API
   │   ├─> Searches mailboxes
   │   ├─> Retrieves email threads
   │   ├─> Performs deduplication
   │   └─> Saves emails and attachments
   │
   └─> Publishes DOCUMENTS_RETRIEVED event
   │
3. Text Extraction Phase
   │
   ├─> Celery worker processes documents
   │   │
   │   ├─> PDF: PyPDF extraction
   │   ├─> Word: python-docx extraction
   │   ├─> Email: mail-parser extraction
   │   └─> Updates extracted_text field
   │
4. Classification Phase
   │
   ├─> Classification Agent detects unclassified documents
   │   │
   │   ├─> Batches documents (10 at a time)
   │   ├─> Calls GPT-4 for each document
   │   ├─> Receives classification + exemptions
   │   ├─> Stores AI classification and confidence
   │   └─> Marks redaction_required if needed
   │
   └─> Publishes CLASSIFICATION_COMPLETE event
   │
5. Review Phase
   │
   ├─> Human reviewer accesses dashboard
   │   │
   │   ├─> Reviews AI classifications
   │   ├─> Approves or overrides decisions
   │   ├─> Marks final_classification
   │   └─> Adds review_notes
   │
6. Redaction Phase
   │
   ├─> Documents marked redaction_required
   │   │
   │   ├─> AI identifies specific content to redact
   │   ├─> Stores redaction_areas (page, coordinates)
   │   └─> Human reviewer confirms redactions
   │
7. Response Generation
   │
   ├─> All documents classified and reviewed
   │   │
   │   ├─> Generate response letter
   │   ├─> List responsive documents
   │   ├─> List withheld documents with exemptions
   │   └─> Package for release
   │
8. Final Release
   │
   └─> Request marked RELEASED
       │
       ├─> Notification sent to requester
       ├─> Response logged in audit trail
       └─> Documents made available for download
```

### AI Classification Pipeline

```
┌────────────────────────────────────────────────────────┐
│               Document Classifier                       │
│                                                         │
│  Input:                                                │
│  ┌──────────────────────────────────────────────┐    │
│  │ - Document text content                       │    │
│  │ - Request description                         │    │
│  │ - Document metadata (author, date, type)      │    │
│  └──────────────────────────────────────────────┘    │
│                                                         │
│  Processing:                                           │
│  ┌──────────────────────────────────────────────┐    │
│  │ 1. Truncate text to 15,000 chars              │    │
│  │ 2. Build context with metadata                │    │
│  │ 3. Construct prompt with Texas PIA guidelines │    │
│  │ 4. Call GPT-4 with JSON response format       │    │
│  │ 5. Parse and validate response                │    │
│  │ 6. Normalize confidence scores                │    │
│  └──────────────────────────────────────────────┘    │
│                                                         │
│  Output:                                               │
│  ┌──────────────────────────────────────────────┐    │
│  │ - classification: responsive/non_responsive   │    │
│  │ - confidence: 0.0 - 1.0                       │    │
│  │ - exemptions: [                               │    │
│  │     {                                         │    │
│  │       category: "attorney_client_privilege",  │    │
│  │       section: "552.107",                     │    │
│  │       confidence: 0.92,                       │    │
│  │       reasoning: "Legal advice to client"     │    │
│  │     }                                         │    │
│  │   ]                                           │    │
│  │ - redaction_needed: true/false                │    │
│  │ - redaction_areas: ["Page 3: SSN"]            │    │
│  │ - reasoning: "Overall explanation"            │    │
│  │ - key_indicators: ["attorney", "privileged"]  │    │
│  └──────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐
│     User        │
│─────────────────│
│ id              │──┐
│ email           │  │
│ hashed_password │  │
│ full_name       │  │
│ role            │  │
│ is_active       │  │
└─────────────────┘  │
                     │ assigned_to
                     │
┌─────────────────┐  │     ┌──────────────────┐
│  PIARequest     │◄─┘     │  WorkflowTask    │
│─────────────────│         │──────────────────│
│ id              │◄────┐   │ id               │
│ request_number  │     │   │ pia_request_id   │
│ requester_name  │     │   │ task_type        │
│ description     │     │   │ task_name        │
│ status          │     │   │ status           │
│ priority        │     │   │ sequence_order   │
│ date_received   │     │   │ assigned_to      │
│ response_deadline│    │   │ started_at       │
│ total_documents │     │   │ completed_at     │
│ total_pages     │     │   │ result_data      │
└─────────────────┘     │   └──────────────────┘
        │               │
        │ pia_request_id│
        │               │
┌─────────────────┐     │   ┌──────────────────┐
│   Document      │─────┘   │   AuditLog       │
│─────────────────│         │──────────────────│
│ id              │─────┐   │ id               │
│ pia_request_id  │     │   │ pia_request_id   │
│ filename        │     │   │ action           │
│ file_path       │     │   │ user_id          │
│ file_hash       │     │   │ details          │
│ document_type   │     │   │ timestamp        │
│ page_count      │     │   └──────────────────┘
│ extracted_text  │     │
│ ai_classification│    │
│ ai_confidence   │     │   ┌──────────────────┐
│ final_classification│ │   │  EmailRecord     │
│ redaction_required│  │   │──────────────────│
│ is_duplicate    │     │   │ id               │
└─────────────────┘     │   │ pia_request_id   │
        │               │   │ message_id       │
        │ document_id   │   │ subject          │
        │               │   │ sender           │
┌─────────────────┐     │   │ recipients       │
│ DocumentLabel   │─────┘   │ thread_id        │
│─────────────────│         │ is_duplicate     │
│ id              │         │ duplicate_of_id  │
│ document_id     │         └──────────────────┘
│ label           │
│ label_type      │         ┌──────────────────┐
│ applied_by      │         │DocClassification │
│ ai_generated    │         │──────────────────│
└─────────────────┘         │ id               │
                            │ document_id      │
                            │ classification   │
                            │ confidence_score │
                            │ reasoning        │
                            │ model_name       │
                            │ exemption_section│
                            │ is_final         │
                            └──────────────────┘
```

### Key Tables

#### pia_requests
Stores all PIA request information:
- Request metadata (number, requester, description)
- Status tracking and workflow state
- Deadline information (received, response, extension, AG ruling)
- Document statistics and counts
- Processing flags

#### documents
Stores all document records:
- File information (path, size, hash, type)
- Text extraction results
- Source information (SharePoint, OneDrive, etc.)
- Classification results (AI and final)
- Redaction requirements
- Deduplication tracking

#### workflow_tasks
Tracks individual workflow steps:
- Task type and sequencing
- Assignment and scheduling
- Progress tracking
- Results and errors
- Celery task integration

#### email_records
Specialized storage for emails:
- Email metadata (sender, recipients, subject)
- Thread grouping information
- Deduplication tracking
- Links to request

#### audit_logs
Complete audit trail:
- All user actions
- System events
- State changes
- Timestamps and user attribution

## Microsoft 365 Integration

### Microsoft Graph API Architecture

```
┌────────────────────────────────────────────────────────┐
│            MS Graph Client                              │
│                                                         │
│  Authentication:                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │ MSAL (Microsoft Authentication Library)       │    │
│  │ - Client Credentials Flow                     │    │
│  │ - Application Permissions                     │    │
│  │ - Token Caching (1 hour TTL)                  │    │
│  │ - Automatic Refresh                           │    │
│  └──────────────────────────────────────────────┘    │
│                                                         │
│  Services:                                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐        │
│  │ SharePoint │ │  OneDrive  │ │  Outlook   │        │
│  │  Service   │ │  Service   │ │  Service   │        │
│  └────────────┘ └────────────┘ └────────────┘        │
└────────────────────────────────────────────────────────┘
```

### SharePoint Service
- Site enumeration and search
- Document library access
- File download with metadata
- Version history retrieval
- Permission checking

### OneDrive Service
- User drive access
- File search by content and metadata
- Batch file downloads
- Sharing information retrieval

### Outlook Service
- Mailbox search
- Email retrieval with attachments
- Thread identification
- Calendar access (for deadline tracking)

## Security Architecture

### Authentication & Authorization

```
┌────────────────────────────────────────────────────────┐
│                  Security Layers                        │
│                                                         │
│  Layer 1: API Authentication                           │
│  ┌──────────────────────────────────────────────┐    │
│  │ - JWT Token (HS256 signing)                   │    │
│  │ - Access Token: 30 min TTL                    │    │
│  │ - Refresh Token: 7 day TTL                    │    │
│  │ - Token stored in httpOnly cookies            │    │
│  └──────────────────────────────────────────────┘    │
│                                                         │
│  Layer 2: Role-Based Access Control                   │
│  ┌──────────────────────────────────────────────┐    │
│  │ Roles:                                        │    │
│  │ - Admin: Full system access                   │    │
│  │ - Coordinator: Manage requests, review docs   │    │
│  │ - Reviewer: Review classifications            │    │
│  │ - Viewer: Read-only access                    │    │
│  └──────────────────────────────────────────────┘    │
│                                                         │
│  Layer 3: Data Protection                             │
│  ┌──────────────────────────────────────────────┐    │
│  │ - HTTPS/TLS for all communications            │    │
│  │ - Password hashing with bcrypt                │    │
│  │ - Encrypted database connections              │    │
│  │ - Secure file storage with access controls    │    │
│  └──────────────────────────────────────────────┘    │
│                                                         │
│  Layer 4: Audit Logging                               │
│  ┌──────────────────────────────────────────────┐    │
│  │ - All actions logged with user attribution    │    │
│  │ - Immutable audit trail                       │    │
│  │ - Document access tracking                    │    │
│  │ - Classification decision recording           │    │
│  └──────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling

1. **Application Layer**
   - Stateless API servers (multiple instances behind load balancer)
   - Shared Redis for session management
   - Connection pooling for database access

2. **Processing Layer**
   - Multiple Celery workers for parallel processing
   - Queue-based task distribution
   - Agent replication for high-volume workloads

3. **Data Layer**
   - PostgreSQL read replicas for query scaling
   - Redis cluster for distributed caching
   - Azure Blob Storage for file scaling

### Performance Optimizations

- Database indexing on frequently queried fields
- Lazy loading of document text content
- Pagination for large result sets
- Response caching for dashboard statistics
- Batch processing for AI classifications
- Connection pooling and keep-alive

### Monitoring Points

- Request processing times
- Agent health and uptime
- Database query performance
- API response times
- Queue depth and processing rate
- Storage utilization
- Classification throughput

## Technology Decisions

### Why FastAPI?
- Modern async support for I/O-bound operations
- Automatic OpenAPI documentation
- Excellent performance (comparable to Node.js)
- Type hints and Pydantic validation
- Large ecosystem and community

### Why PostgreSQL?
- Strong ACID compliance for legal requirements
- JSON field support for flexible metadata
- Excellent full-text search capabilities
- Mature replication and backup tools
- Wide hosting support

### Why Celery?
- Proven distributed task queue
- Redis integration for low latency
- Retry and error handling built-in
- Scheduled task support (Celery Beat)
- Monitoring tools (Flower)

### Why Agent-Based Architecture?
- Modular, maintainable codebase
- Independent scaling of components
- Fault isolation and recovery
- Clear separation of concerns
- Easier testing and debugging

### Why GPT-4 for Classification?
- Superior understanding of legal language
- Context-aware reasoning
- Consistent classification logic
- Explainable decisions (reasoning provided)
- Fine-tuning capabilities for domain expertise
