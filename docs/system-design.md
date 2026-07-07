# System Design Document
# AI Support Operations Platform

**Version:** 1.0  
**Created:** 2026-06-20  

---

## 1. HIGH-LEVEL ARCHITECTURE
┌─────────────────────────────────────────────────────────────┐
│ CLIENT LAYER │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ React SPA │ │ Mobile App │ │ Third-Party │ │
│ │ (Vercel) │ │ (Future) │ │ Integrations│ │
│ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │
│ │ │ │ │
│ └─────────────────┼─────────────────┘ │
│ │ HTTPS │
└───────────────────────────┼──────────────────────────────────┘
│
┌───────────────────────────┼──────────────────────────────────┐
│ API GATEWAY LAYER │
│ ┌────────┴────────┐ │
│ │ FastAPI App │ │
│ │ (Render) │ │
│ └────────┬────────┘ │
│ │ │
└───────────────────────────┼──────────────────────────────────┘
│
┌───────────────────────────┼──────────────────────────────────┐
│ SERVICE LAYER │
│ ┌────────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ Auth Service │ │ Ticket Svc │ │ AI Service │ │
│ │ - JWT │ │ - CRUD │ │ - Classify │ │
│ │ - RBAC │ │ - Comments │ │ - Embeddings │ │
│ │ - Permissions │ │ - Search │ │ - RAG │ │
│ └───────┬────────┘ └──────┬───────┘ └──────┬───────┘ │
│ │ │ │ │
└──────────┼─────────────────┼─────────────────┼────────────────┘
│ │ │
┌──────────┼─────────────────┼─────────────────┼────────────────┐
│ DATA LAYER │
│ ┌───────┴─────────────────┴─────────────────┴───────┐ │
│ │ PostgreSQL + pgvector │ │
│ │ (Tickets, Users, Organizations) │ │
│ └──────────────────────────┬───────────────────────┘ │
│ │ │
│ ┌──────────────────────────┴───────────────────────┐ │
│ │ ChromaDB (Vector Store) │ │
│ │ (Embeddings, Similarity Search) │ │
│ └──────────────────────────────────────────────────┘ │
│ │
│ ┌──────────────────────────────────────────────────┐ │
│ │ External AI APIs (Gemini) │ │
│ └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘

---

## 2. BACKEND ARCHITECTURE (CLEAN ARCHITECTURE)
backend/app/
│
├── api/ ← Interface Adapters Layer
│ ├── v1/
│ │ ├── auth.py ← Auth endpoints
│ │ ├── tickets.py ← Ticket endpoints
│ │ ├── comments.py ← Comment endpoints
│ │ └── ai.py ← AI endpoints
│ └── deps/
│ ├── auth.py ← Auth dependency injection
│ └── database.py ← DB session dependency
│
├── services/ ← Application Business Logic
│ ├── auth_service.py ← Authentication logic
│ ├── ticket_service.py ← Ticket business rules
│ ├── comment_service.py ← Comment logic
│ └── ai_service.py ← AI orchestration
│
├── models/ ← Enterprise Entities (DB)
│ ├── user.py
│ ├── organization.py
│ ├── ticket.py
│ └── comment.py
│
├── schemas/ ← Data Transfer Objects
│ ├── user.py
│ ├── ticket.py
│ └── ai.py
│
├── ai/ ← AI Modules (Domain Logic)
│ ├── embeddings/
│ │ └── embedder.py ← Text to vector conversion
│ ├── classification/
│ │ └── classifier.py ← Ticket classification
│ ├── generation/
│ │ └── generator.py ← AI reply generation
│ └── rag/
│ └── retriever.py ← Knowledge base search
│
├── db/ ← Database Layer
│ ├── session.py ← SQLAlchemy session factory
│ └── base.py ← Declarative base class
│
└── core/ ← Configuration & Cross-cutting
├── config.py ← Environment settings
├── security.py ← JWT, password hashing
└── exceptions.py ← Custom error handlers

text

---

## 3. DATABASE DESIGN

### 3.1 Entity Relationship Diagram
┌──────────────┐ ┌──────────────┐
│ Organization │ │ User │
├──────────────┤ ├──────────────┤
│ id (PK) │←──────│ org_id (FK) │
│ name │ │ id (PK) │
│ slug (unique)│ │ email │
│ created_at │ │ password_hash│
└──────────────┘ │ full_name │
│ role │
│ created_at │
└──────┬───────┘
│
│ created_by
│
┌──────────────┐ ┌──────┴───────┐
│ Comment │ │ Ticket │
├──────────────┤ ├──────────────┤
│ id (PK) │ │ id (PK) │
│ ticket_id(FK)│←──────│ org_id (FK) │
│ user_id (FK) │ │ created_by │
│ body │ │ assigned_to │
│ parent_id │ │ title │
│ created_at │ │ description │
└──────────────┘ │ status │
│ priority │
│ category │
│ ai_category │
│ ai_priority │
│ sentiment │
│ health_score │
│ created_at │
│ updated_at │
└──────────────┘

text

### 3.2 Database Choice: PostgreSQL + pgvector

**Why PostgreSQL:**
- ACID compliance for ticket data
- JSONB for flexible metadata
- pgvector extension for embeddings
- Row-level security for multi-tenancy
- Mature, well-supported

**Why not MongoDB:**
- Tickets have relational data (users, orgs, comments)
- Need transactions (ticket + comment creation)
- SQL is better for reporting/analytics

---

## 4. API DESIGN

### 4.1 REST API Convention
Base URL: /api/v1

Authentication:
POST /auth/register ← Create account
POST /auth/login ← Get JWT token
POST /auth/refresh ← Refresh token

Organizations:
POST /organizations ← Create org
GET /organizations/{id} ← Get org details
PUT /organizations/{id} ← Update org
GET /organizations/{id}/users ← List org users

Tickets:
POST /tickets ← Create ticket
GET /tickets ← List tickets (paginated)
GET /tickets/{id} ← Get ticket detail
PUT /tickets/{id} ← Update ticket
DELETE /tickets/{id} ← Delete ticket
GET /tickets/{id}/similar ← Find similar tickets (AI)
POST /tickets/{id}/ai-reply ← Generate AI reply

Comments:
POST /tickets/{id}/comments ← Add comment
GET /tickets/{id}/comments ← List comments
PUT /comments/{id} ← Edit comment
DELETE /comments/{id} ← Delete comment

Dashboard:
GET /dashboard/stats ← Ticket statistics
GET /dashboard/trends ← Trend data

text

### 4.2 Request/Response Format

```json
// Success Response
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150
  }
}

// Error Response
{
  "success": false,
  "error": {
    "code": "TICKET_NOT_FOUND",
    "message": "Ticket with id 123 not found"
  }
}
5. AUTHENTICATION FLOW
text
┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client  │         │  Server  │         │ Database │
└────┬─────┘         └────┬─────┘         └────┬─────┘
     │                    │                    │
     │  POST /auth/login  │                    │
     │  {email, password} │                    │
     │───────────────────>│                    │
     │                    │  SELECT user       │
     │                    │───────────────────>│
     │                    │  user row          │
     │                    │<───────────────────│
     │                    │                    │
     │                    │  Verify password   │
     │                    │  Generate JWT      │
     │                    │                    │
     │  {access_token,    │                    │
     │   refresh_token}   │                    │
     │<───────────────────│                    │
     │                    │                    │
     │  GET /tickets      │                    │
     │  Authorization:    │                    │
     │  Bearer <token>    │                    │
     │───────────────────>│                    │
     │                    │  Verify JWT        │
     │                    │  Extract user_id   │
     │                    │  Check permissions │
     │                    │                    │
     │  Ticket list       │                    │
     │<───────────────────│                    │
6. AI PIPELINE DESIGN
text
┌─────────────────────────────────────────────────────────┐
│                    AI REQUEST FLOW                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Ticket Created ──> Preprocessing ──> Classification     │
│                                       │                  │
│                                       ├──> Category     │
│                                       └──> Priority     │
│                                            │             │
│  ┌─────────────────────────────────────────┘             │
│  │                                                       │
│  ├──> Generate Embedding ──> Store in ChromaDB           │
│  │                                                       │
│  ├──> Similar Ticket Search ──> Return top 5             │
│  │                                                       │
│  └──> AI Reply Generation ──> Gemini API ──> Draft       │
│                                                          │
│  Background Jobs (Phase 3):                              │
│  ├──> Sentiment Analysis                                 │
│  └──> Health Score Update                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
AI Technology Stack:
Embeddings: Sentence Transformers (all-MiniLM-L6-v2) - 384 dimensions

Vector DB: ChromaDB - lightweight, Python-native

LLM: Google Gemini API - classification + generation

Fallback: Rule-based classification if AI fails

7. MULTI-TENANCY DESIGN
text
┌─────────────────────────────────────────────────────────┐
│                  MULTI-TENANT ISOLATION                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Strategy: Shared Database, Separate Schema (Row-Level) │
│                                                          │
│  Every table has: org_id (Foreign Key)                  │
│                                                          │
│  Query Filtering:                                       │
│  ┌─────────────────────────────────────────────┐        │
│  │ SELECT * FROM tickets                       │        │
│  │ WHERE org_id = current_user.org_id          │        │
│  │   AND user has permission to view           │        │
│  └─────────────────────────────────────────────┘        │
│                                                          │
│  Why this approach:                                      │
│  ✅ Simple to implement                                  │
│  ✅ Cost-effective (single DB)                           │
│  ✅ Easy cross-org analytics (future)                    │
│  ❌ Risk of data leak if query filter missed             │
│  Mitigation: Base repository class always adds filter    │
│                                                          │
└─────────────────────────────────────────────────────────┘
8. DEPLOYMENT ARCHITECTURE
text
┌─────────────────────────────────────────────────────────┐
│                     DEPLOYMENT                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Vercel    │  │   Render    │  │  Render      │      │
│  │  (React)    │  │  (FastAPI)  │  │ (PostgreSQL) │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                          │
│  GitHub ──> CI/CD Pipeline ──> Automated Tests           │
│                │                                          │
│                ├──> Build Docker Image                    │
│                ├──> Push to Registry                      │
│                └──> Deploy to Render                      │
│                                                          │
│  Environment Variables (Render Dashboard):               │
│  - DATABASE_URL                                           │
│  - JWT_SECRET_KEY                                         │
│  - GEMINI_API_KEY                                         │
│  - CHROMADB_PATH                                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
9. KEY DESIGN DECISIONS
Decision	Options Considered	Why This Choice
FastAPI vs Django	Django, Flask, FastAPI	Async support, auto-docs, type hints
PostgreSQL vs MongoDB	Both viable	Relational data, ACID, pgvector
ChromaDB vs Pinecone	Pinecone, Weaviate	Free, local dev, Python-native
JWT vs Session Auth	Both	Stateless, mobile-ready, no server storage
Clean Architecture	MVC, DDD	Testable, modular, interview-friendly
pgvector vs separate DB	Separate vector DB	Simpler deployment, one DB
10. PERFORMANCE REQUIREMENTS
API Response: < 200ms (p95) for CRUD operations

AI Classification: < 2 seconds (async)

Similar Ticket Search: < 500ms

Concurrent Users: 100+ on basic hardware

Database: Connection pooling (20 connections)

Caching: Redis for frequent queries (Phase 5)

text

---

## Learning Notes File

Create file: `project-notes/system-design-notes.md`

```markdown
# System Design Learning Notes

## What This Document Is
The blueprint of HOW we build the system - architecture patterns, data flow, and technology decisions.

## Key Architecture Patterns Used

### 1. Clean Architecture (Robert C. Martin)
- **Entities (models/):** Core business objects
- **Use Cases (services/):** Business logic
- **Interface Adapters (api/):** HTTP concerns
- **Frameworks (FastAPI):** External tools

**Why:** Each layer can be tested independently. You can swap FastAPI for Flask without changing business logic.

### 2. Repository Pattern
Instead of writing SQL in API routes, we create a service layer that handles all business logic. API routes just call services.

### 3. Dependency Injection
FastAPI's `Depends()` provides DB sessions and auth checks automatically. Makes testing easy - just mock dependencies.

## Interview Questions This Document Answers

**Q: Design a customer support ticket system.**
A: Walk through this document - 3-tier architecture, REST APIs, database schema, AI pipeline.

**Q: How do you handle multi-tenancy?**
A: Row-level security with org_id on every table. Discuss trade-offs vs separate databases.

**Q: Why PostgreSQL instead of MongoDB?**
A: Tickets have relational data (users → tickets → comments). Need ACID transactions. pgvector gives us vector search without another database.

**Q: How do you make AI responses fast?**
A: Async processing. Classification happens immediately. Generation and embeddings happen in background. Cache similar ticket results.

**Q: What's your API versioning strategy?**
A: URL-based versioning (/api/v1/). Allows breaking changes in v2 without affecting existing clients.

## Key Trade-offs Made

| Decision | Alternative | Why We Chose This |
|----------|-------------|-------------------|
| Clean Architecture | Simple MVC | Testability, interview value |
| JWT | Sessions | Stateless, scales horizontally |
| ChromaDB | Pinecone | Free for dev, simpler setup |
| Row-level multi-tenancy | Separate databases | Cost-effective for MVP |

## System Design Interview Tips

1. Always start with requirements (PRD)
2. Draw the high-level architecture first
3. Then dive into database schema
4. Discuss trade-offs openly
5. Mention what you'd improve with more time
Summary
✅ System Design Document created - Complete architecture blueprint
✅ Learning notes created - Ready for system design interviews


