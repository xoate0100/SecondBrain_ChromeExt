# Master Unified API Strategy

**Version:** 1.0  
**Date:** January 27, 2025  
**Status:** AUTHORITATIVE  
**Purpose:** Tool-independent API design framework for Second Brain system

---

## Table of Contents

1. [API Architecture Philosophy](#1-api-architecture-philosophy)
2. [Request/Response Standards](#2-requestresponse-standards)
3. [Authentication & Authorization](#3-authentication--authorization)
4. [Core API Endpoints Specification](#4-core-api-endpoints-specification)
5. [Webhook Infrastructure](#5-webhook-infrastructure)
6. [External Tool Integration Guide](#6-external-tool-integration-guide)
7. [Error Handling & Validation](#7-error-handling--validation)
8. [Performance & Scalability](#8-performance--scalability)
9. [Testing Requirements](#9-testing-requirements)
10. [Documentation Standards](#10-documentation-standards)

---

## 1. API Architecture Philosophy

### 1.1 Tool-Independent Design Principles

The Second Brain API is designed to be **tool-independent**, meaning:

- **Internal Development**: FastAPI routes use the same patterns as external tools
- **External Tools**: Chrome extensions, Alexa skills, and other integrations follow identical patterns
- **Consistency**: All API consumers (internal or external) experience the same interface
- **Scalability**: Architecture supports single-user to multi-tenant scenarios

### 1.2 SOLID Principles Application

#### Single Responsibility Principle (SRP)
- **Route Handlers**: Handle HTTP request/response only
- **Service Layer**: Contains business logic (`CoreAutomationService`)
- **Data Models**: Represent domain entities only
- **Validators**: Validate input/output only

**Example Structure:**
```
Route Handler (src/api/routes/capture.py)
    ↓
Service Layer (src/core/automation_service.py)
    ↓
Core Logic (src/core/processors/, src/core/classifiers/)
```

#### Open/Closed Principle (OCP)
- API endpoints are **open for extension** via new routes
- Core service logic is **closed for modification** but extensible via dependency injection
- New capture sources extend base `CaptureHandler` interface

#### Liskov Substitution Principle (LSP)
- All authentication methods (JWT, API Key, OAuth) implement `AuthenticationProvider` interface
- All capture sources implement `CaptureSource` interface
- Service implementations are interchangeable

#### Interface Segregation Principle (ISP)
- Clients depend only on interfaces they use
- External tools only need `CaptureAPI` interface, not full `CoreAutomationService`
- Webhook clients only need `WebhookAPI` interface

#### Dependency Inversion Principle (DIP)
- Route handlers depend on `CoreAutomationService` abstraction, not concrete implementation
- Services depend on interfaces (e.g., `AIClient`, `StorageProvider`)
- Configuration injected via `AutomationConfig` dataclass

### 1.3 Dependency Injection Patterns

**FastAPI Dependency Pattern:**
```python
# src/api/dependencies.py
def get_automation_service() -> CoreAutomationService:
    """Dependency to get automation service"""
    if not automation_service:
        raise HTTPException(status_code=503, detail="Service not available")
    return automation_service

# Route handler
@app.post("/api/v1/capture")
async def capture(
    request: CaptureRequest,
    service: CoreAutomationService = Depends(get_automation_service),
):
    """Capture endpoint using dependency injection"""
    return await service.process_capture(request)
```

**Service Layer Pattern:**
```python
# Services injected via constructor
class CoreAutomationService:
    def __init__(self, config: AutomationConfig):
        self.config = config
        self.ollama_client = OllamaClient(...)  # Injected
        self.openai_client = OpenAIAPIClient(...)  # Injected
        self.state_manager = StateManager()  # Injected
```

### 1.4 Separation of Concerns

**Three-Layer Architecture:**

1. **API Layer** (`src/api/`)
   - HTTP request/response handling
   - Input validation (Pydantic models)
   - Authentication/authorization checks
   - Error response formatting

2. **Service Layer** (`src/core/`)
   - Business logic orchestration
   - Cross-cutting concerns (logging, metrics)
   - Transaction management
   - Service composition

3. **Domain Layer** (`src/core/processors/`, `src/core/classifiers/`)
   - Core business rules
   - Domain models
   - Algorithm implementations
   - Data transformations

### 1.5 Versioning Strategy

**Semantic Versioning with URL Prefix:**

- **Current Version**: `/api/v1/`
- **Breaking Changes**: Increment to `/api/v2/`
- **Non-Breaking Changes**: Add new endpoints to `/api/v1/`
- **Deprecation**: Announce 90 days before removal

**Versioning Rules:**
- Adding new optional fields: **Same version**
- Adding new endpoints: **Same version**
- Removing fields: **New version**
- Changing field types: **New version**
- Changing required fields: **New version**

**Example:**
```
/api/v1/capture          # Current
/api/v1/capture/v2       # Future (if needed)
/api/v2/capture          # Breaking changes
```

---

## 2. Request/Response Standards

### 2.1 Consistent JSON Schema

All requests MUST use JSON with `Content-Type: application/json` header.

**Request Structure:**
```json
{
  "data": {
    // Request-specific payload
  },
  "metadata": {
    "idempotency_key": "optional-uuid",
    "source": "chrome-extension",
    "version": "1.0"
  }
}
```

### 2.2 Standardized Response Envelope

**Success Response:**
```json
{
  "success": true,
  "data": {
    // Response-specific payload
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": "2025-01-27T12:00:00Z",
    "processing_time_ms": 150
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "title",
      "reason": "Title is required"
    }
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": "2025-01-27T12:00:00Z"
  }
}
```

### 2.3 Error Response Structure

**Error Code Taxonomy:**
- `VALIDATION_ERROR`: Input validation failed (400)
- `AUTHENTICATION_ERROR`: Invalid credentials (401)
- `AUTHORIZATION_ERROR`: Insufficient permissions (403)
- `NOT_FOUND`: Resource not found (404)
- `CONFLICT`: Resource conflict (409)
- `RATE_LIMIT_EXCEEDED`: Too many requests (429)
- `INTERNAL_ERROR`: Server error (500)
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable (503)

**Error Response Format:**
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {
      // Additional context
    },
    "trace_id": "optional-trace-id"
  }
}
```

### 2.4 Pagination Patterns

**List Endpoints Pagination:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 150,
    "total_pages": 3,
    "has_next": true,
    "has_previous": false
  }
}
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 100)
- `sort`: Sort field (default: "created_at")
- `order`: Sort order "asc" or "desc" (default: "desc")

### 2.5 Idempotency Requirements

**Idempotency Key Pattern:**
- Client provides `idempotency_key` in request metadata
- Server stores key with request result
- Duplicate requests with same key return cached result
- Key expires after 24 hours

**Idempotency Key Format:**
- UUID v4 recommended
- Must be unique per client operation
- Stored in `X-Idempotency-Key` header or request metadata

**Example:**
```http
POST /api/v1/capture
X-Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "data": { ... }
}
```

---

## 3. Authentication & Authorization

### 3.1 JWT Token Strategy

**JWT Configuration** (from `config/security/security-config.yaml`):
- **Algorithm**: HS256
- **Access Token Expiry**: 60 minutes (production), 480 minutes (development)
- **Refresh Token Expiry**: 7 days
- **Secret Key**: Stored in `JWT_SECRET_KEY` environment variable

**JWT Token Structure:**
```json
{
  "sub": "user_id",
  "exp": 1234567890,
  "iat": 1234567890,
  "scope": ["capture:write", "read:notes"],
  "source": "internal"
}
```

**JWT Usage:**
- Primary authentication for internal API calls
- Stored in `Authorization: Bearer <token>` header
- Automatically refreshed via refresh token endpoint

### 3.2 API Key Management

**API Key Format:**
- Prefix: `sb_` (Second Brain)
- Format: `sb_live_...` or `sb_test_...`
- Length: 32+ characters
- Stored hashed in database

**API Key Scopes:**
- `capture:write`: Create captures
- `conversations:read`: Read conversations
- `conversations:write`: Import conversations
- `files:read`: Read files
- `files:write`: Import files
- `webhooks:manage`: Manage webhooks

**API Key Usage:**
- Primary authentication for external tools
- Stored in `Authorization: Bearer <api_key>` header
- Rate limited per key (100 req/min default)

**API Key Management Endpoints:**
```
POST   /api/v1/auth/api-keys          # Create API key
GET    /api/v1/auth/api-keys          # List API keys
DELETE /api/v1/auth/api-keys/{id}     # Revoke API key
```

### 3.3 OAuth 2.0 Integration

**OAuth 2.0 Flow** (reusing Google Workspace patterns):
- **Authorization Code Flow**: For web applications
- **Client Credentials Flow**: For service-to-service
- **Token Storage**: Per-account credential storage (see `GoogleAPIClient`)

**OAuth Scopes:**
- `read:captures`: Read capture data
- `write:captures`: Create captures
- `read:conversations`: Read conversations
- `write:conversations`: Import conversations

**OAuth Endpoints:**
```
GET  /api/v1/auth/oauth/authorize     # Authorization endpoint
POST /api/v1/auth/oauth/token         # Token endpoint
POST /api/v1/auth/oauth/refresh       # Refresh token
```

### 3.4 Rate Limiting Per Authentication Method

**Rate Limit Configuration** (from `config/security/security-config.yaml`):
- **JWT (Internal)**: 1000 req/min (development), 100 req/min (production)
- **API Keys (External)**: 100 req/min per key
- **OAuth Tokens**: 500 req/min per token
- **Unauthenticated**: 10 req/min per IP

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

**Rate Limit Response:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Retry after 60 seconds.",
    "retry_after": 60
  }
}
```

### 3.5 Security Headers and CORS Policies

**Security Headers** (from `config/security/security-config.yaml`):
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

**CORS Configuration:**
- **Allowed Origins**: Configured per environment
- **Allowed Methods**: GET, POST, PUT, DELETE
- **Allowed Headers**: Content-Type, Authorization, X-Requested-With
- **Credentials**: Supported for authenticated requests

---

## 4. Core API Endpoints Specification

### 4.1 Universal Capture Endpoint

**Endpoint:** `POST /api/v1/capture`

**Purpose:** Universal endpoint for all capture sources (Alexa, Chrome extension, iOS, etc.)

**Request Schema:**
```json
{
  "data": {
    "title": "Note title",
    "content": "Note content or body text",
    "source": "alexa|chrome-extension|ios|email|manual|other",
    "metadata": {
      "is_startable": false,
      "effort_estimate_min": 15,
      "location": "home-office|shop|field|remote",
      "voice_transcript": "optional voice transcript",
      "attachments": [
        {
          "type": "image|file|url",
          "url": "https://...",
          "filename": "optional filename"
        }
      ]
    }
  },
  "metadata": {
    "idempotency_key": "optional-uuid",
    "source_version": "1.0"
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "data": {
    "capture_id": "20250127-1200-capture-uuid",
    "status": "processing|completed|failed",
    "note_id": "20250127-1200-kebab-title",
    "processing_status": {
      "step": "ai_classification|ai_summary|validation",
      "progress": 0.75
    }
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": "2025-01-27T12:00:00Z",
    "processing_time_ms": 150
  }
}
```

**Status Codes:**
- `201 Created`: Capture created successfully
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

**Validation Rules:**
- `title`: Required, min 1 character, max 200 characters
- `content`: Required, min 1 character, max 1MB
- `source`: Required, must be valid enum value
- `is_startable`: If true, `effort_estimate_min` required
- `effort_estimate_min`: If provided, must be 5-120 minutes

### 4.2 Conversation Import Endpoint

**Endpoint:** `POST /api/v1/conversations/import`

**Purpose:** Import conversations from ChatGPT, Claude, or other AI chat platforms

**Request Schema:**
```json
{
  "data": {
    "conversation_id": "chat-123",
    "platform": "chatgpt|claude|other",
    "messages": [
      {
        "role": "user|assistant|system",
        "content": "Message content",
        "timestamp": "2025-01-27T12:00:00Z"
      }
    ],
    "metadata": {
      "model": "gpt-4",
      "title": "Conversation title",
      "created_at": "2025-01-27T12:00:00Z",
      "tags": ["optional", "tags"]
    }
  },
  "metadata": {
    "idempotency_key": "optional-uuid",
    "batch_id": "optional-batch-identifier"
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "data": {
    "conversation_id": "chat-123",
    "import_id": "import-uuid",
    "notes_created": 3,
    "actions_extracted": 5,
    "status": "completed|processing|failed",
    "notes": [
      {
        "note_id": "20250127-1200-note-id",
        "title": "Extracted note title",
        "status": "ready|inbox"
      }
    ]
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": "2025-01-27T12:00:00Z",
    "processing_time_ms": 2500
  }
}
```

**Status Codes:**
- `201 Created`: Import started successfully
- `202 Accepted`: Import queued for processing
- `400 Bad Request`: Invalid conversation data
- `409 Conflict`: Conversation already imported

**Batch Import:**
- Use `batch_id` in metadata to group related imports
- Process up to 100 conversations per batch
- Returns batch status endpoint URL

### 4.3 File Import from Drive Endpoint

**Endpoint:** `POST /api/v1/files/import-from-drive`

**Purpose:** Import files from Google Drive or other cloud storage

**Request Schema:**
```json
{
  "data": {
    "file_id": "drive-file-123",
    "file_name": "document.md",
    "content": "file content (text)",
    "mime_type": "text/markdown|text/plain|application/pdf|image/png",
    "drive_metadata": {
      "account": "user@gmail.com",
      "folder_path": "/Projects/Notes",
      "file_url": "https://drive.google.com/...",
      "modified_time": "2025-01-27T12:00:00Z"
    },
    "options": {
      "ocr_enabled": true,
      "extract_text_from_pdf": true,
      "process_immediately": true
    }
  },
  "metadata": {
    "idempotency_key": "optional-uuid",
    "source": "google-drive-sync"
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "data": {
    "file_id": "drive-file-123",
    "import_id": "import-uuid",
    "note_id": "20250127-1200-file-title",
    "status": "processing|completed|failed",
    "extracted_text": "OCR or extracted text content",
    "processing_status": {
      "ocr_completed": true,
      "text_extracted": true,
      "classification_completed": false
    }
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": "2025-01-27T12:00:00Z"
  }
}
```

**Status Codes:**
- `201 Created`: File import started
- `400 Bad Request`: Invalid file data
- `413 Payload Too Large`: File exceeds size limit (100MB)
- `415 Unsupported Media Type`: File type not supported

**Supported File Types:**
- Markdown: `.md`, `.markdown`
- Text: `.txt`, `.text`
- PDF: `.pdf` (with OCR)
- Images: `.png`, `.jpg`, `.jpeg` (with OCR)

### 4.4 Capture Status Endpoint

**Endpoint:** `GET /api/v1/capture/status/{capture_id}`

**Purpose:** Check processing status of a capture

**Response Schema:**
```json
{
  "success": true,
  "data": {
    "capture_id": "20250127-1200-capture-uuid",
    "status": "processing|completed|failed",
    "note_id": "20250127-1200-kebab-title",
    "processing_steps": {
      "normalization": "completed",
      "ai_classification": "completed",
      "ai_summary": "in_progress",
      "validation": "pending"
    },
    "progress": 0.75,
    "estimated_completion": "2025-01-27T12:01:00Z",
    "errors": [],
    "warnings": []
  },
  "metadata": {
    "request_id": "uuid",
    "timestamp": "2025-01-27T12:00:00Z"
  }
}
```

**Status Codes:**
- `200 OK`: Status retrieved
- `404 Not Found`: Capture not found

---

## 5. Webhook Infrastructure

### 5.1 Webhook Registration

**Endpoint:** `POST /api/v1/webhooks/register`

**Purpose:** Register a webhook URL to receive events

**Request Schema:**
```json
{
  "data": {
    "url": "https://example.com/webhook",
    "events": [
      "capture.completed",
      "note.created",
      "note.updated"
    ],
    "secret": "webhook-secret-for-hmac",
    "active": true
  }
}
```

**Response Schema:**
```json
{
  "success": true,
  "data": {
    "webhook_id": "webhook-uuid",
    "url": "https://example.com/webhook",
    "events": ["capture.completed", "note.created"],
    "status": "active|inactive",
    "created_at": "2025-01-27T12:00:00Z",
    "verification_status": "pending|verified|failed"
  }
}
```

### 5.2 Webhook Verification

**Endpoint:** `GET /api/v1/webhooks/{webhook_id}/verify`

**Purpose:** Verify webhook endpoint is reachable

**Verification Process:**
1. Server sends `GET` request to webhook URL with `challenge` parameter
2. Client must respond with `challenge` value in response body
3. Server marks webhook as verified

**Challenge Response:**
```json
{
  "challenge": "challenge-string-from-query-param"
}
```

### 5.3 Webhook Event Delivery

**Endpoint:** `POST /webhook/{webhook_id}` (external, called by Second Brain)

**Purpose:** Deliver events to registered webhooks

**Event Payload:**
```json
{
  "event": "capture.completed",
  "timestamp": "2025-01-27T12:00:00Z",
  "data": {
    "capture_id": "20250127-1200-capture-uuid",
    "note_id": "20250127-1200-kebab-title",
    "status": "completed"
  },
  "signature": "hmac-sha256-signature"
}
```

**HMAC Signature:**
- Algorithm: HMAC-SHA256
- Secret: Webhook secret from registration
- Payload: JSON stringified event data
- Header: `X-Webhook-Signature`

**Signature Verification:**
```python
import hmac
import hashlib

def verify_signature(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### 5.4 Retry Logic and Queue Management

**Retry Strategy:**
- **Initial Retry**: 1 second after failure
- **Exponential Backoff**: 2s, 4s, 8s, 16s, 32s
- **Max Retries**: 5 attempts
- **Timeout**: 30 seconds per attempt

**Retry Conditions:**
- HTTP 5xx errors: Retry
- HTTP 429 (Rate Limit): Retry with backoff
- HTTP 4xx errors: Do not retry
- Network errors: Retry
- Timeout: Retry

**Queue Management:**
- Failed webhooks stored in retry queue
- Queue processed asynchronously
- Dead letter queue after max retries

### 5.5 Event Types and Payload Schemas

**Event Types:**
- `capture.created`: New capture created
- `capture.completed`: Capture processing completed
- `capture.failed`: Capture processing failed
- `note.created`: Note created from capture
- `note.updated`: Note updated
- `note.status_changed`: Note status changed
- `conversation.imported`: Conversation imported
- `file.imported`: File imported

**Event Payload Schema:**
```json
{
  "event": "event.type",
  "timestamp": "ISO8601",
  "data": {
    // Event-specific data
  },
  "metadata": {
    "event_id": "uuid",
    "source": "second-brain-api"
  }
}
```

### 5.6 Webhook Security Best Practices

1. **HTTPS Required**: All webhook URLs must use HTTPS
2. **HMAC Verification**: Always verify webhook signatures
3. **Secret Rotation**: Rotate webhook secrets periodically
4. **IP Whitelisting**: Optional IP whitelist for webhook endpoints
5. **Idempotency**: Webhook handlers should be idempotent
6. **Timeout Handling**: Handle timeouts gracefully

---

## 6. External Tool Integration Guide

### 6.1 Chrome Extension Integration

**Architecture:**
- Content scripts inject into ChatGPT/Claude pages
- Background service worker handles API communication
- Storage API for offline queue

**Integration Pattern:**
```javascript
// Background service worker
async function captureConversation(conversationData) {
  const response = await fetch('https://api.secondbrain.com/api/v1/conversations/import', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'X-Idempotency-Key': generateUUID()
    },
    body: JSON.stringify({
      data: {
        conversation_id: conversationData.id,
        platform: 'chatgpt',
        messages: conversationData.messages,
        metadata: {
          model: conversationData.model,
          title: conversationData.title
        }
      }
    })
  });
  
  if (!response.ok) {
    // Queue for retry
    await queueForRetry(conversationData);
    return;
  }
  
  return await response.json();
}
```

**Error Handling:**
- Network errors: Queue for retry
- 429 Rate Limit: Exponential backoff
- 401 Unauthorized: Prompt for API key
- 400 Bad Request: Log error, skip

**Offline Queue:**
- Store failed requests in `chrome.storage.local`
- Retry on next successful connection
- Limit queue size to 100 items

### 6.2 Alexa Skill Integration

**Architecture:**
- AWS Lambda function handles skill logic
- Webhook to Second Brain API
- Session management for multi-turn interactions

**Integration Pattern:**
```python
# AWS Lambda handler
import requests

def handle_capture_intent(intent, session):
    """Handle Alexa capture intent"""
    api_key = os.environ['SECOND_BRAIN_API_KEY']
    api_url = os.environ['SECOND_BRAIN_API_URL']
    
    # Extract slot values
    title = intent['slots']['title']['value']
    content = intent['slots']['content']['value']
    is_startable = intent['slots']['is_startable']['value'] == 'yes'
    effort_min = intent['slots']['effort_min']['value'] or 15
    
    # Call Second Brain API
    response = requests.post(
        f'{api_url}/api/v1/capture',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        json={
            'data': {
                'title': title,
                'content': content,
                'source': 'alexa',
                'metadata': {
                    'is_startable': is_startable,
                    'effort_estimate_min': int(effort_min),
                    'voice_transcript': content
                }
            }
        }
    )
    
    if response.status_code == 201:
        return "Note captured successfully"
    else:
        return "Sorry, I couldn't capture that note"
```

**Intent Schema:**
```json
{
  "intents": [
    {
      "name": "AddNoteIntent",
      "slots": [
        {"name": "title", "type": "AMAZON.SearchQuery"},
        {"name": "content", "type": "AMAZON.SearchQuery"}
      ]
    },
    {
      "name": "AddStartableIntent",
      "slots": [
        {"name": "title", "type": "AMAZON.SearchQuery"},
        {"name": "content", "type": "AMAZON.SearchQuery"},
        {"name": "effort_min", "type": "AMAZON.NUMBER"}
      ]
    }
  ]
}
```

### 6.3 Google Drive Sync Integration

**Architecture:**
- Background service monitors Google Drive folders
- Google Drive API for file changes
- OAuth 2.0 for authentication (reuse `GoogleAPIClient` patterns)

**Integration Pattern:**
```python
# Google Drive sync service
from src.services.google_api_client import GoogleAPIClient

class GoogleDriveSyncService:
    def __init__(self, api_client: GoogleAPIClient):
        self.api_client = api_client
        self.second_brain_api = SecondBrainAPIClient()
    
    async def sync_file(self, file_id: str, account_email: str):
        """Sync file from Google Drive to Second Brain"""
        # Fetch file from Drive
        file_data = await self.api_client.get_file(file_id, account_email)
        
        # Import to Second Brain
        response = await self.second_brain_api.import_file(
            file_id=file_id,
            file_name=file_data['name'],
            content=file_data['content'],
            mime_type=file_data['mimeType'],
            drive_metadata={
                'account': account_email,
                'folder_path': file_data.get('parents', [])[0],
                'file_url': file_data['webViewLink'],
                'modified_time': file_data['modifiedTime']
            }
        )
        
        return response
```

**Webhook Integration:**
- Register webhook for `file.imported` events
- Update local state when files imported
- Handle conflicts (file modified in both places)

### 6.4 SDK/Client Library Requirements

**Python SDK:**
```python
from secondbrain import SecondBrainClient

client = SecondBrainClient(
    api_key='your-api-key',
    base_url='https://api.secondbrain.com'
)

# Capture
result = client.capture(
    title='Note title',
    content='Note content',
    source='manual',
    is_startable=True,
    effort_estimate_min=15
)

# Import conversation
result = client.import_conversation(
    conversation_id='chat-123',
    platform='chatgpt',
    messages=[...]
)
```

**JavaScript SDK:**
```javascript
import { SecondBrainClient } from '@secondbrain/sdk';

const client = new SecondBrainClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.secondbrain.com'
});

// Capture
const result = await client.capture({
  title: 'Note title',
  content: 'Note content',
  source: 'manual',
  isStartable: true,
  effortEstimateMin: 15
});
```

### 6.5 Testing Strategies for External Tools

**Mock API Server:**
- Use tools like `wiremock` or `mockserver`
- Simulate API responses for testing
- Test error scenarios (429, 500, etc.)

**Integration Testing:**
- Test against staging API environment
- Use test API keys with higher rate limits
- Verify webhook delivery

**Error Scenario Testing:**
- Network failures
- API rate limiting
- Invalid authentication
- Malformed responses

---

## 7. Error Handling & Validation

### 7.1 Pydantic Model Validation Patterns

**Request Model Example:**
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class CaptureRequest(BaseModel):
    """Capture request model"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=1_000_000)
    source: str = Field(..., regex="^(alexa|chrome-extension|ios|email|manual|other)$")
    metadata: Optional[CaptureMetadata] = None
    
    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Example note",
                "content": "Note content",
                "source": "manual"
            }
        }
```

**Validation Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "field": "title",
      "reason": "Title cannot be empty",
      "value": ""
    }
  }
}
```

### 7.2 Custom Exception Hierarchy

**Exception Structure:**
```python
class SecondBrainAPIError(Exception):
    """Base API exception"""
    pass

class ValidationError(SecondBrainAPIError):
    """Validation error (400)"""
    pass

class AuthenticationError(SecondBrainAPIError):
    """Authentication error (401)"""
    pass

class AuthorizationError(SecondBrainAPIError):
    """Authorization error (403)"""
    pass

class NotFoundError(SecondBrainAPIError):
    """Resource not found (404)"""
    pass

class RateLimitError(SecondBrainAPIError):
    """Rate limit exceeded (429)"""
    pass

class InternalError(SecondBrainAPIError):
    """Internal server error (500)"""
    pass
```

**Exception Handler:**
```python
@app.exception_handler(SecondBrainAPIError)
async def api_exception_handler(request, exc):
    """Handle API exceptions"""
    status_code = 500
    if isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, AuthenticationError):
        status_code = 401
    # ... etc
    
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": exc.__class__.__name__.upper(),
                "message": str(exc),
                "details": getattr(exc, "details", {})
            }
        }
    )
```

### 7.3 Error Code Taxonomy

**Error Codes:**
- `VALIDATION_ERROR`: Input validation failed
- `AUTHENTICATION_ERROR`: Invalid credentials
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `CONFLICT`: Resource conflict (e.g., duplicate)
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server error
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable
- `TIMEOUT`: Request timeout
- `BAD_GATEWAY`: Upstream service error

### 7.4 Input Sanitization Requirements

**Sanitization Rules:**
1. **HTML Escaping**: Escape HTML in user input
2. **SQL Injection**: Use parameterized queries
3. **XSS Prevention**: Sanitize all output
4. **Path Traversal**: Validate file paths
5. **Size Limits**: Enforce request size limits (10MB default)

**Sanitization Example:**
```python
import html
from pathlib import Path

def sanitize_input(value: str) -> str:
    """Sanitize user input"""
    # HTML escape
    value = html.escape(value)
    # Remove control characters
    value = ''.join(c for c in value if ord(c) >= 32)
    return value.strip()

def validate_file_path(path: str) -> bool:
    """Validate file path (prevent traversal)"""
    resolved = Path(path).resolve()
    vault_path = Path("/vault").resolve()
    return str(resolved).startswith(str(vault_path))
```

### 7.5 Logging and Monitoring Patterns

**Structured Logging:**
```python
import logging
import json

logger = logging.getLogger(__name__)

def log_api_request(request, response, duration_ms):
    """Log API request with structured data"""
    logger.info(
        "API request",
        extra={
            "request_id": request.state.request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": getattr(request.state, "user_id", None)
        }
    )
```

**Error Logging:**
```python
def log_error(error: Exception, context: dict):
    """Log error with context"""
    logger.error(
        f"API error: {error}",
        exc_info=True,
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context
        }
    )
```

**Monitoring Metrics:**
- Request rate (requests/second)
- Error rate (errors/second)
- Response time (p50, p95, p99)
- Active connections
- Queue depth

---

## 8. Performance & Scalability

### 8.1 Response Time Targets

**Performance Requirements** (from `docs/constraints/ai-development-standards.md`):
- **API Response Time**: ≤200ms (p95)
- **File Processing**: ≤60s (p95)
- **Memory Usage**: ≤512MB per request
- **CPU Usage**: ≤80% average

**Performance Monitoring:**
- Track response times per endpoint
- Alert on p95 > 200ms
- Monitor slow queries
- Profile hot paths

### 8.2 Async/Await Patterns for I/O Operations

**Async Pattern:**
```python
@app.post("/api/v1/capture")
async def capture(
    request: CaptureRequest,
    service: CoreAutomationService = Depends(get_automation_service),
):
    """Async capture endpoint"""
    # Non-blocking I/O operations
    result = await service.process_capture_async(request)
    return result
```

**Async Service Methods:**
```python
class CoreAutomationService:
    async def process_capture_async(self, request: CaptureRequest):
        """Async capture processing"""
        # Parallel operations
        tasks = [
            self.ai_client.generate_summary(request.content),
            self.ai_client.classify(request.content),
            self.state_manager.save_capture(request)
        ]
        results = await asyncio.gather(*tasks)
        return results
```

### 8.3 Caching Strategies

**Cache Layers:**
1. **Response Caching**: Cache GET responses (5 minutes)
2. **Query Result Caching**: Cache database queries (1 minute)
3. **AI Response Caching**: Cache AI classification results (1 hour)

**Cache Implementation:**
```python
from functools import lru_cache
import redis

redis_client = redis.Redis(host='localhost', port=6379)

@lru_cache(maxsize=1000)
def get_cached_classification(content_hash: str):
    """Cache classification results"""
    cache_key = f"classification:{content_hash}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

def set_cached_classification(content_hash: str, result: dict, ttl: int = 3600):
    """Set cached classification"""
    cache_key = f"classification:{content_hash}"
    redis_client.setex(
        cache_key,
        ttl,
        json.dumps(result)
    )
```

### 8.4 Rate Limiting Configuration

**Rate Limit Implementation:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/capture")
@limiter.limit("100/minute")
async def capture(request: Request, ...):
    """Rate-limited capture endpoint"""
    ...
```

**Per-Key Rate Limiting:**
```python
def get_api_key(request: Request) -> str:
    """Extract API key from request"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return ""

@app.post("/api/v1/capture")
@limiter.limit("100/minute", key_func=get_api_key)
async def capture(request: Request, ...):
    """Rate-limited by API key"""
    ...
```

### 8.5 Horizontal Scaling Considerations

**Stateless Design:**
- No server-side session storage
- All state in database or cache
- Requests can be handled by any instance

**Load Balancing:**
- Round-robin or least-connections
- Health check endpoints for load balancer
- Sticky sessions not required

**Database Scaling:**
- Read replicas for read-heavy endpoints
- Connection pooling
- Query optimization

**Cache Scaling:**
- Redis cluster for distributed caching
- Cache warming strategies
- Cache invalidation patterns

---

## 9. Testing Requirements

### 9.1 TDD Approach for API Endpoints

**Red-Green-Refactor-Document Cycle:**

**1. Red Phase: Write Failing Test**
```python
def test_capture_endpoint_creates_note():
    """Test capture endpoint creates note"""
    client = TestClient(app)
    response = client.post(
        "/api/v1/capture",
        json={
            "data": {
                "title": "Test note",
                "content": "Test content",
                "source": "manual"
            }
        }
    )
    assert response.status_code == 201
    assert response.json()["success"] is True
    assert "capture_id" in response.json()["data"]
```

**2. Green Phase: Minimal Implementation**
```python
@app.post("/api/v1/capture")
async def capture(request: CaptureRequest):
    """Minimal implementation to pass test"""
    return {
        "success": True,
        "data": {"capture_id": "test-id"}
    }
```

**3. Refactor Phase: Improve Implementation**
```python
@app.post("/api/v1/capture")
async def capture(
    request: CaptureRequest,
    service: CoreAutomationService = Depends(get_automation_service),
):
    """Refactored implementation with service layer"""
    result = await service.process_capture(request)
    return {
        "success": True,
        "data": result
    }
```

**4. Document Phase: Update Documentation**
- Update OpenAPI spec
- Add examples
- Document error scenarios

### 9.2 Test Coverage Requirements

**Coverage Requirements:**
- **Unit Tests**: 100% coverage (NO EXCEPTIONS)
- **Integration Tests**: 100% coverage (NO EXCEPTIONS)
- **E2E Tests**: 100% coverage for critical paths

**Test Organization:**
```
tests/
├── unit/
│   ├── test_api_routes.py
│   ├── test_validation.py
│   └── test_authentication.py
├── integration/
│   ├── test_capture_flow.py
│   ├── test_conversation_import.py
│   └── test_webhook_delivery.py
└── e2e/
    └── test_full_pipeline.py
```

### 9.3 Integration Test Patterns

**Integration Test Example:**
```python
@pytest.mark.asyncio
async def test_capture_to_note_pipeline():
    """Test full capture to note pipeline"""
    # Setup
    client = TestClient(app)
    api_key = create_test_api_key()
    
    # Capture
    capture_response = client.post(
        "/api/v1/capture",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "data": {
                "title": "Test note",
                "content": "Test content",
                "source": "manual"
            }
        }
    )
    assert capture_response.status_code == 201
    capture_id = capture_response.json()["data"]["capture_id"]
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Check status
    status_response = client.get(
        f"/api/v1/capture/status/{capture_id}",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert status_response.status_code == 200
    assert status_response.json()["data"]["status"] == "completed"
```

### 9.4 Mock Strategies for External Dependencies

**Mock AI Client:**
```python
@pytest.fixture
def mock_ai_client():
    """Mock AI client for testing"""
    with patch('src.services.ollama_client.OllamaClient') as mock:
        mock.return_value.generate_summary.return_value = "Test summary"
        mock.return_value.classify.return_value = {
            "venture": "Personal",
            "domain": "admin"
        }
        yield mock
```

**Mock External API:**
```python
from unittest.mock import patch
import responses

@responses.activate
def test_webhook_delivery():
    """Test webhook delivery with mocked endpoint"""
    responses.add(
        responses.POST,
        "https://example.com/webhook",
        json={"received": True},
        status=200
    )
    
    # Test webhook delivery
    result = deliver_webhook(webhook_url, event_data)
    assert result.success is True
```

### 9.5 API Contract Testing

**Contract Testing:**
- Use tools like `pact` or `schemathesis`
- Test API contracts between services
- Verify request/response schemas
- Test backward compatibility

**Example:**
```python
import schemathesis

schema = schemathesis.from_file("openapi.yaml")

@schema.parametrize()
def test_api_contract(case):
    """Test API contract"""
    response = case.call()
    case.validate_response(response)
```

---

## 10. Documentation Standards

### 10.1 OpenAPI/Swagger Specification Requirements

**OpenAPI Specification:**
- All endpoints MUST have OpenAPI documentation
- Use OpenAPI 3.0.3 specification
- Include request/response schemas
- Include authentication requirements
- Include error responses

**Example:**
```yaml
paths:
  /api/v1/capture:
    post:
      summary: Create a new capture
      description: Universal endpoint for capturing notes from any source
      tags:
        - Capture
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CaptureRequest'
      responses:
        '201':
          description: Capture created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CaptureResponse'
        '400':
          $ref: '#/components/responses/ValidationError'
        '401':
          $ref: '#/components/responses/AuthenticationError'
```

### 10.2 Endpoint Documentation Template

**Template:**
```markdown
## Endpoint Name

**Method:** `POST /api/v1/endpoint`

**Purpose:** Brief description of endpoint purpose

**Authentication:** Required (JWT/API Key/OAuth)

**Request:**
- **Schema:** Link to OpenAPI schema
- **Example:** JSON example
- **Validation Rules:** List of validation rules

**Response:**
- **Success (201):** Response schema and example
- **Errors:** List of possible error responses

**Rate Limits:** 100 requests/minute

**Example Request:**
\`\`\`bash
curl -X POST https://api.secondbrain.com/api/v1/endpoint \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"data": {...}}'
\`\`\`

**Example Response:**
\`\`\`json
{
  "success": true,
  "data": {...}
}
\`\`\`
```

### 10.3 Request/Response Examples

**Include Examples For:**
- All request types (minimal and full)
- All response types (success and errors)
- Edge cases (empty strings, null values)
- Real-world scenarios

**Example Format:**
```json
{
  "examples": {
    "minimal": {
      "data": {
        "title": "Note",
        "content": "Content",
        "source": "manual"
      }
    },
    "full": {
      "data": {
        "title": "Complete Note",
        "content": "Full content with details",
        "source": "chrome-extension",
        "metadata": {
          "is_startable": true,
          "effort_estimate_min": 30,
          "location": "home-office"
        }
      },
      "metadata": {
        "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
      }
    }
  }
}
```

### 10.4 Error Scenario Documentation

**Document All Error Scenarios:**
- Validation errors with examples
- Authentication errors
- Authorization errors
- Rate limiting
- Service unavailable
- Timeout errors

**Error Documentation Format:**
```markdown
### Error: VALIDATION_ERROR

**Status Code:** 400

**Cause:** Input validation failed

**Example:**
\`\`\`json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Title is required",
    "details": {
      "field": "title",
      "reason": "Field is required"
    }
  }
}
\`\`\`

**Resolution:** Ensure all required fields are provided
```

### 10.5 Integration Examples for External Tools

**Chrome Extension Example:**
```javascript
// Complete working example
const apiKey = 'your-api-key';
const apiUrl = 'https://api.secondbrain.com';

async function captureConversation(conversation) {
  try {
    const response = await fetch(`${apiUrl}/api/v1/conversations/import`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'X-Idempotency-Key': crypto.randomUUID()
      },
      body: JSON.stringify({
        data: {
          conversation_id: conversation.id,
          platform: 'chatgpt',
          messages: conversation.messages,
          metadata: {
            model: conversation.model,
            title: conversation.title
          }
        }
      })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Capture failed:', error);
    // Queue for retry
    await queueForRetry(conversation);
  }
}
```

**Alexa Skill Example:**
```python
# Complete working example
import os
import requests

def handle_capture(intent, session):
    api_key = os.environ['SECOND_BRAIN_API_KEY']
    api_url = os.environ['SECOND_BRAIN_API_URL']
    
    title = intent['slots']['title']['value']
    content = intent['slots']['content']['value']
    
    response = requests.post(
        f'{api_url}/api/v1/capture',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        json={
            'data': {
                'title': title,
                'content': content,
                'source': 'alexa'
            }
        },
        timeout=10
    )
    
    if response.status_code == 201:
        return "Note captured successfully"
    else:
        return "Sorry, I couldn't capture that note"
```

---

## Appendix A: Quick Reference

### A.1 Base URL
```
Production: https://api.secondbrain.com/api/v1
Staging: https://staging-api.secondbrain.com/api/v1
Development: http://localhost:8080/api/v1
```

### A.2 Authentication Methods
- **JWT**: `Authorization: Bearer <jwt_token>`
- **API Key**: `Authorization: Bearer <api_key>`
- **OAuth 2.0**: `Authorization: Bearer <oauth_token>`

### A.3 Common Headers
```http
Authorization: Bearer <token>
Content-Type: application/json
X-Idempotency-Key: <uuid>
X-Request-ID: <uuid>
```

### A.4 Common Status Codes
- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Authorization failed
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service unavailable

---

## Appendix B: Changelog

### Version 1.0 (2025-01-27)
- Initial API strategy document
- Core endpoints defined
- Authentication framework established
- Webhook infrastructure specified
- External tool integration guides created

---

**Last Updated:** January 27, 2025  
**Status:** AUTHORITATIVE  
**Next Review:** April 27, 2025

