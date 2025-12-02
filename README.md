# Texas PIA Request Automation System

A comprehensive automation platform for processing Public Information Act (PIA) requests under Texas Government Code Chapter 552. Built for the City of San Antonio to streamline document retrieval, classification, and compliance management.

## Overview

The Texas PIA Request Automation System reduces manual document review workload by 60-70% through intelligent automation. It integrates with Microsoft 365 to retrieve documents and emails, applies machine learning-based classification against Texas PIA exemptions, and provides a complete workflow management interface.

## Key Features

- **Automated Document Retrieval** - Connects to SharePoint, OneDrive, and Outlook to automatically gather responsive documents
- **Intelligent Classification** - Classifies documents according to Texas Government Code Chapter 552 exemption categories
- **Email Thread Consolidation** - Groups email conversations and identifies the optimal email for review, reducing review volume by 40%+
- **Deadline Management** - Tracks 10-day response deadlines with automated notifications and escalation
- **Redaction Detection** - Identifies PII, privileged information, and other content requiring redaction
- **Workflow Automation** - Manages the complete request lifecycle from receipt through release
- **Real-time Dashboard** - Provides visibility into request status, workload distribution, and compliance metrics
- **Audit Trail** - Comprehensive logging for legal compliance and transparency

## Tech Stack

### Backend
- **Framework:** FastAPI 0.109.0
- **Language:** Python 3.11+
- **Database:** PostgreSQL 15 with async SQLAlchemy
- **Cache/Queue:** Redis 7 with Celery
- **Authentication:** Azure AD / JWT

### Frontend
- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS
- **State:** Zustand + React Query

### Integrations
- **Microsoft Graph API** - SharePoint, OneDrive, Outlook access
- **OpenAI API** - Document classification engine
- **Azure Services** - Authentication, Storage, Container Apps

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Azure AD application registration (for M365 integration)
- OpenAI API key

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/pia-automation.git
cd pia-automation

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/api/v1/docs
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Yes |
| `AZURE_TENANT_ID` | Azure AD tenant ID | Yes |
| `AZURE_CLIENT_ID` | Azure AD application ID | Yes |
| `AZURE_CLIENT_SECRET` | Azure AD client secret | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `CORS_ORIGINS` | Allowed CORS origins | No |
| `DEBUG` | Enable debug mode | No |

## Project Structure

```
pia-automation/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # API endpoints
│   │   ├── core/             # Configuration, database, security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   │   ├── agents/       # Autonomous processing agents
│   │   │   ├── ai/           # Classification, extraction
│   │   │   ├── documents/    # Document processing
│   │   │   ├── microsoft/    # M365 integration
│   │   │   └── workflow/     # Workflow engine
│   │   └── main.py           # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   ├── pages/            # Page components
│   │   └── services/         # API services
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── API.md
├── docker-compose.yml
└── README.md
```

## API Documentation

Interactive API documentation is available at `/api/v1/docs` when the server is running.

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/requests` | GET, POST | List/create PIA requests |
| `/api/v1/requests/{id}` | GET | Get request details |
| `/api/v1/requests/{id}/start-processing` | POST | Start automated processing |
| `/api/v1/documents` | GET | List documents for a request |
| `/api/v1/documents/{id}/classify` | POST | Trigger classification |
| `/api/v1/emails` | GET | List emails for a request |
| `/api/v1/workflow/tasks` | GET | Get workflow tasks |
| `/api/v1/dashboard/overview` | GET | Dashboard metrics |

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest --cov=app tests/

# Frontend tests
cd frontend
npm test
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code:
- Passes all existing tests
- Includes tests for new functionality
- Follows the existing code style
- Updates documentation as needed

## Texas PIA Compliance

This system is designed to support compliance with Texas Government Code Chapter 552, including:

- **10 Business Day Response** - Automatic deadline calculation excluding state holidays
- **Exemption Categories** - Classification against all major exemption categories (552.101-552.143)
- **Extension Management** - Support for 10-day extensions with proper documentation
- **AG Ruling Workflow** - Support for Attorney General ruling requests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Developed for the City of San Antonio, City Secretary's Office and Legal Department.
