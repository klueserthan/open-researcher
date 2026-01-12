# Data Models Overview

This document provides a comprehensive overview of all data models in Open Notebook, derived from the SurrealDB schema migrations.

## Core Entities

### user
**Purpose**: Represents system users with authentication and authorization

| Field | Type | Description |
|-------|------|-------------|
| `id` | record<user> | Unique identifier |
| `email` | string | User email (unique, indexed) |
| `username` | string | Username (unique index) |
| `password` | string | Hashed password |
| `first_name` | option<string> | User's first name |
| `last_name` | option<string> | User's last name |
| `is_active` | bool | Account active status (default: true) |
| `is_superuser` | bool | Admin privileges (default: false) |
| `created_at` | datetime | Account creation timestamp |
| `updated_at` | datetime | Last modification timestamp |

---

### **notebook**
User's research workspace containing sources, notes, and chat sessions.

**Fields:**
- `id`: record<notebook>
- `name`: string
- `description`: option<string>
- `user_id`: record<user>
- `created_at`: datetime (default: now)
- `updated_at`: datetime (default: now)
- `default_model`: option<string> - Default AI model for this notebook

---

#### **source**
Individual content items uploaded to notebooks (files, URLs, or text).

- `id`: record<source>
- `notebook_id`: record<notebook>
- `user_id`: record<user>
- `title`: string
- `content`: option<string>
- `source_type`: string (enum: file, url, text)
- `filename`: option<string>
- `url`: option<string>
- `file_type`: option<string>
- `file_size`: option<int>
- `mime_type`: option<string>
- `status`: string (enum: pending, processing, completed, failed)
- `error_message`: option<string>
- `created_at`: datetime (default: now)
- `updated_at`: datetime (default: now)
- `embedding_model`: option<string>
- `command`: option<record<command>>

#### **note**
- `id`: record<note>
- `notebook_id`: record<notebook>
- `user_id`: record<user>
- `title`: string
- `content`: string
- `note_type`: string (enum: brief, faq, study_guide, timeline, custom)
- `created_at`: datetime (default: now)
- `updated_at`: datetime (default: now)

#### **chat_session**
- `id`: record<chat_session>
- `notebook_id`: record<notebook>
- `user_id`: record<user>
- `title`: string
- `created_at`: datetime (default: now)
- `updated_at`: datetime (default: now)
- `model_override`: option<string>

#### **chat_message**
- `id`: record<chat_message>
- `chat_session_id`: record<chat_session>
- `user_id`: record<user>
- `role`: string (enum: user, assistant, system)
- `content`: string
- `created_at`: datetime (default: now)

#### **command**
- `id`: record<command>
- `notebook_id`: option<record<notebook>>
- `user_id`: record<user>
- `command_type`: string (enum: generate_note, generate_podcast, vectorize_source)
- `status`: string (enum: pending, processing, completed, failed)
- `input_data`: option<object>
- `output_data`: option<object>
- `error_message`: option<string>
- `created_at`: datetime (default: now)
- `updated_at`: datetime (default: now)
- `completed_at`: option<datetime>

#### **podcast**
- `id`: record<podcast>
- `notebook_id`: record<notebook>
- `user_id`: record<user>
- `title`: string
- `description`: option<string>
- `audio_url`: option<string>
- `transcript`: option<string>
- `duration`: option<int>
- `status`: string (enum: pending, processing, completed, failed)
- `error_message`: option<string>
- `created_at`: datetime (default: now)
- `updated_at`: datetime (default: now)

### Relationships

#### **belongs_to** (RELATION)
- FROM: `notebook | source | note | chat_session | chat_message | command | podcast`
- TO: `user`

#### **contains** (RELATION)
- FROM: `notebook`
- TO: `source | note | chat_session | podcast`

#### **part_of** (RELATION)
- FROM: `chat_message`
- TO: `chat_session`

#### **refers_to** (RELATION)
- FROM: `chat_session`
- TO: `notebook | source`

## Indexes

- **user.email**: Unique index
- **user.username**: Unique index

## Key Features

1. **Multi-tenancy**: All entities linked to `user_id` for data isolation
2. **Hierarchical structure**: Notebooks contain sources, notes, chat sessions, and podcasts
3. **Async processing**: `command` table tracks long-running operations (podcasts, vectorization)
4. **Chat flexibility**: Chat sessions can reference either notebooks or sources
5. **Model overrides**: Both `notebook` and `chat_session` support custom model selection
6. **Status tracking**: Sources, commands, and podcasts have status enums for workflow management
7. **Graph relationships**: SurrealDB relations enable efficient queries across entity boundaries
