# STATEMENT OF WORK

## Texas Public Information Act (PIA) Automation System
### Rapid Build Project

**Project Reference:** SOW-2025-PIA-RAPID-001
**Date:** November 24, 2025
**Revision:** 2.0

---

## PARTIES

**Contractor:**
The AI Cowboys
Austin, Texas

**Client:**
City of San Antonio
City Secretary's Office / Legal Department
San Antonio, Texas

---

## 1. EXECUTIVE SUMMARY

The AI Cowboys will design, develop, and deploy a production-ready Texas PIA automation system using modern rapid deployment practices and proven architectural patterns. This project leverages:

- Pre-built integration patterns for Microsoft 365
- Proven FastAPI + React architecture templates
- Azure deployment automation
- Parallel workstream execution
- Machine learning-based document classification

**Target Outcomes:**
- 60-70% reduction in manual document review
- Automated compliance with 10-day response deadline
- Working production system, not just a demo

---

## 2. TECHNOLOGY STACK

- **Backend:** Python 3.11 + FastAPI
- **Frontend:** React 18 + TypeScript + Tailwind CSS
- **ML/Classification:** OpenAI GPT-4 / Azure OpenAI
- **Database:** PostgreSQL + SQLAlchemy (async)
- **Cache/Queue:** Redis + Celery
- **Integration:** Microsoft Graph API
- **Deployment:** Docker + Azure Container Apps

---

## 3. DELIVERABLES

### 3.1 Core System Components

| Component | Description | Status |
|-----------|-------------|--------|
| PIA Request Management | Create, track, manage requests | Included |
| Document Retrieval | SharePoint, OneDrive integration | Included |
| Email Retrieval | Outlook search and retrieval | Included |
| Document Classification | Texas PIA exemption detection | Included |
| Email Deduplication | Thread grouping, duplicate removal | Included |
| Redaction Detection | PII, privilege, medical info flagging | Included |
| Dashboard | Real-time metrics and status | Included |
| Workflow Engine | Automated task management | Included |
| Deadline Tracking | 10-day compliance management | Included |
| Azure AD SSO | Single sign-on authentication | Included |

### 3.2 Documentation

- System architecture overview
- API documentation (OpenAPI/Swagger)
- User quick-start guide
- Administrator guide
- Deployment runbook

### 3.3 Training

- 2-hour administrator training session
- 1-hour end-user training session
- Recorded training videos

---

## 4. SUCCESS CRITERIA

| Metric | Target | Measurement |
|--------|--------|-------------|
| Manual Review Reduction | 60-70% | Before/after comparison |
| Classification Accuracy | >85% | Sample validation |
| Email Deduplication | >40% reduction | Processing statistics |
| System Response Time | <2 seconds | API monitoring |
| User Adoption | Operational | Training completion |
| Deadline Compliance | Tracking functional | System demonstration |

---

## 5. TECHNICAL SPECIFICATIONS

### 5.1 Texas PIA Exemption Categories

| Category | Section | Supported |
|----------|---------|-----------|
| Responsive | N/A | Yes |
| Non-Responsive | N/A | Yes |
| Attorney-Client Privilege | 552.107 | Yes |
| Legislative Privilege | 552.008 | Yes |
| Law Enforcement | 552.108 | Yes |
| Medical Information | 552.101/HIPAA | Yes |
| Personnel Records | 552.102 | Yes |
| Trade Secrets | 552.110 | Yes |
| Deliberative Process | 552.111 | Yes |
| Personal Information | 552.101 | Yes |

### 5.2 Supported Document Types

| Type | Extension | Extraction |
|------|-----------|------------|
| PDF | .pdf | Full text |
| Word | .doc, .docx | Full text |
| Excel | .xls, .xlsx | All sheets |
| Email | .eml, .msg | Body + metadata |
| Text | .txt | Full text |
| Images | .jpg, .png | Optional OCR add-on |

### 5.3 API Endpoints

```
POST   /api/v1/requests              Create PIA request
GET    /api/v1/requests              List requests
GET    /api/v1/requests/{id}         Get request details
POST   /api/v1/requests/{id}/process Start processing

GET    /api/v1/documents             List documents
POST   /api/v1/documents/upload      Upload documents
POST   /api/v1/documents/{id}/classify Classify document
GET    /api/v1/documents/{id}/redactions Get redactions

GET    /api/v1/emails                List emails
GET    /api/v1/emails/threads        List email threads
POST   /api/v1/emails/retrieve       Retrieve from M365

GET    /api/v1/workflow/tasks        List workflow tasks
POST   /api/v1/workflow/tasks/{id}/complete Complete task
GET    /api/v1/workflow/status       Get workflow status

GET    /api/v1/dashboard/overview    Dashboard metrics
GET    /api/v1/dashboard/urgent      Urgent items
GET    /api/v1/dashboard/compliance  Compliance report
```

---

## 6. INFRASTRUCTURE COSTS (Monthly - Client Pays Direct to Azure)

| Service | Estimated Monthly |
|---------|------------------|
| Azure Container Apps | $150-300 |
| Azure PostgreSQL | $100-200 |
| Azure Blob Storage | $50-100 |
| Azure Redis Cache | $50-100 |
| OpenAI API Usage | $300-500 |
| **Estimated Monthly Total** | **$650-1,200** |

---

## 7. PREREQUISITES (Client to Provide)

- [ ] Microsoft 365 admin access for Azure AD app registration
- [ ] Azure subscription for deployment
- [ ] OpenAI API key or Azure OpenAI access
- [ ] Sample PIA request with documents (for testing)
- [ ] List of user mailboxes for email retrieval testing
- [ ] SharePoint site URLs for document retrieval testing
- [ ] Designated test users (3-5 people)

---

## 8. TERMS AND CONDITIONS

### 8.1 Intellectual Property
- All custom code becomes property of City of San Antonio
- The AI Cowboys retains rights to pre-existing tools and methodologies
- Open-source components under respective licenses

### 8.2 Warranty
- 30-day warranty on delivered functionality
- Critical issues addressed within 24 hours
- Standard issues addressed within 72 hours

### 8.3 Confidentiality
- All PIA data treated as confidential
- No data retained after project completion
- NDA available upon request

---

## 9. ACCEPTANCE

This Statement of Work represents a binding agreement for the development and delivery of the Texas PIA Automation System.

**The AI Cowboys**

Signature: ________________________
Name: ___________________________
Title: ___________________________
Date: ___________________________

**City of San Antonio**

Signature: ________________________
Name: ___________________________
Title: ___________________________
Date: ___________________________

---

*This system is designed to significantly reduce manual document review workload while maintaining compliance with Texas Government Code Chapter 552.*
