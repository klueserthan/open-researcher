# Copilot Instructions for Open Notebook

This guide helps AI coding agents understand the Open Notebook codebase architecture, critical workflows, and project-specific conventions.

## Project Overview

**Open Notebook** is a privacy-first, open-source alternative to Google Notebook LM. It's an AI-powered research platform enabling users to upload multi-modal content, generate semantic notes, search intelligently, chat with AI, and produce professional podcasts. Key value: complete data sovereignty + choice of 16+ AI providers.

## Three-Tier Architecture

```
Frontend (React/Next.js, port 3000)
    ↓ HTTP REST
API (FastAPI, port 5055)
    ↓ SurrealQL
Database (SurrealDB graph DB, port 8000)
```

- **Frontend** (`frontend/`): React 19 + Next.js 15, TypeScript, Zustand state, TanStack Query, Shadcn/ui + Tailwind
- **API** (`api/`): FastAPI service layer with Pydantic v2 validation, routes → services → database
- **Core** (`open_notebook/`): Domain models, LangGraph workflows, AI provisioning, database repository pattern, utilities
- **Database**: SurrealDB (graph + vector embeddings), auto-migrations on API startup

## Critical Architecture Patterns

### 1. Async-First Design
All database ops, graph invocations, and AI calls use `async`/`await`. SurrealDB async driver with connection pooling. FastAPI handles concurrency efficiently.

### 2. LangGraph Workflows
State machines for content pipelines:
- **source.py**: File/URL ingestion → extract → embed → save
- **chat.py**: Conversational agent with message history (SqliteSaver checkpoint)
- **ask.py**: Semantic search + synthesis (retrieve context → LLM)
- **transformation.py**: Custom transformations on source content

All workflows call `provision_langchain_model()` for intelligent model selection with fallback.

### 3. Multi-Provider AI (Esperanto)
Unified interface to 16+ providers (OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI, etc.).
- **ModelManager**: Factory pattern with token-aware fallback
- **Smart selection**: Auto-upgrades for large contexts, applies per-request overrides
- **Model override scoping**: Configured per-request via RunnableConfig (not persistent)

### 4. Service Layer Pattern
Three-layer design: Routes → Services → Database/Graphs
- Routes in `api/routers/` (HTTP endpoints)
- Services in `api/*_service.py` (business logic)
- Models in `api/models.py` (Pydantic schemas)
- No DI framework; services imported directly

### 5. Database Repository Pattern
- Repository functions in `open_notebook/database/repository.py`: `repo_query()`, `repo_create()`, `repo_upsert()`, `repo_delete()`
- All async; use SurrealDB transaction syntax
- AutoMigrationManager runs migrations on API startup from `migrations/` directory
- Vector search built-in via SurrealDB

### 6. Fire-and-Forget Embeddings
Source vectorization returns `command_id` immediately without awaiting. Embedding happens asynchronously via surreal-commands job queue. Track status via `/commands/{command_id}` endpoint.

## Key Files & Entry Points

| File/Dir | Purpose |
|----------|---------|
| `api/main.py` | FastAPI app, router registration, auth middleware, lifespan (migrations) |
| `open_notebook/domain/` | Core data models (Notebook, Source, Note, ChatSession, etc.) with search methods |
| `open_notebook/graphs/` | LangGraph workflows (source, chat, ask, transformation) |
| `open_notebook/ai/` | ModelManager, AI provider config, fallback logic |
| `open_notebook/database/` | SurrealDB CRUD, migrations, connection pooling |
| `tests/` | Unit & integration tests (pytest, pytest-asyncio) |
| `Makefile` | Dev commands: `make start-all`, `make api`, `make frontend`, `make database` |
| `pyproject.toml` | Dependencies (FastAPI, LangChain, LangGraph, Esperanto, SurrealDB, etc.) |

## Developer Workflows

### Start Development Environment
```bash
make start-all    # Starts DB + API + Worker + Frontend
make database     # Just database
make api          # Just FastAPI
make frontend     # Just Next.js
make stop-all     # Stop all services
```

### Run Tests
```bash
uv run pytest tests/                    # All tests
uv run pytest tests/test_graphs.py      # Specific test file
uv run pytest --cov                     # Coverage report
```

### Code Quality
```bash
uv run python -m mypy .      # Type checking
ruff check . --fix           # Linting with auto-fix
```

### Add New Endpoint
1. Create `api/routers/feature.py` with FastAPI router
2. Create `api/feature_service.py` with business logic
3. Define request/response schemas in `api/models.py`
4. Register router in `api/main.py`: `app.include_router(router)`
5. Test via `http://localhost:5055/docs` (Swagger UI)

### Add LangGraph Workflow
1. Create `open_notebook/graphs/workflow.py`
2. Define StateDict (input/output schema) and node functions
3. Build with `.add_node()` / `.add_edge()`
4. Invoke in service: `graph.ainvoke({...}, config={...})`
5. Test with sample data in `tests/test_graphs.py`

## Important Quirks & Gotchas

- **Password auth is basic** (dev-only): Production must use OAuth/JWT
- **Graph invocations block**: Chat/podcast workflows may take minutes; no built-in timeout
- **Migrations run on startup**: Database schema migrations auto-run on API startup
- **CORS open by default**: `api/main.py` allows all origins; restrict before production
- **No rate limiting**: Add at proxy layer for production
- **Services are stateless**: Each request re-queries DB/AI; no result caching
- **Command tracking is essential**: Podcast generation returns job ID; must poll `/commands/{id}` to track progress
- **Content processing is sync**: `content_core.extract_content()` may briefly block API
- **Model override doesn't persist**: Config changes via API only apply to current request

## Cross-Component Communication

1. **Frontend → API**: HTTP REST with TanStack Query (auto caching/refetching)
2. **API → Database**: Async SurrealQL via repository functions
3. **API → Graphs**: LangGraph `ainvoke()` with RunnableConfig for model overrides
4. **Graphs → AI Providers**: Esperanto library (unified model interface)
5. **Graphs → Database**: Via repository functions in node callbacks
6. **Async Jobs**: Surreal-commands job queue for long-running operations (podcasts)

## Code Style & Conventions

- **Python**: Black formatting (line length 88), mypy type hints, Pydantic for validation
- **TypeScript**: ESLint config, Tailwind CSS utility-first, Shadcn/ui for components
- **Async patterns**: Use `async`/`await` consistently; no blocking I/O
- **Error handling**: Catch exceptions in services, return HTTP status codes (400, 404, 500)
- **Logging**: Use `loguru` logger in `api/main.py`; services expected to log key operations
- **Testing**: Pytest for Python, organized in `tests/` directory

## Development Practices for AI Agents

### Test-Driven Development (TDD)
**All code changes must follow TDD practices:**

1. **Write tests first**: Before implementing any feature or fix, write failing tests that define the expected behavior
2. **Run tests**: Execute `uv run pytest tests/` to verify tests fail appropriately
3. **Implement code**: Write minimal code to make tests pass
4. **Verify tests pass**: Run `uv run pytest tests/` again to confirm all tests pass
5. **Refactor**: Improve code quality while keeping tests green

### Test Validation Requirements
**Before completing any task, you MUST:**

- ✅ Run `uv run pytest tests/` and verify ALL tests pass (exit code 0)
- ✅ Add tests for new features (test coverage for new code paths)
- ✅ Update existing tests if behavior changes
- ✅ Include both unit tests and integration tests where appropriate
- ✅ Test async functions with `pytest-asyncio`
- ✅ Verify type hints with `uv run python -m mypy .` (no type errors)

**Never submit code that:**
- ❌ Has failing tests
- ❌ Lacks test coverage for new functionality
- ❌ Breaks existing tests without fixing them
- ❌ Introduces type errors

### Test Organization
- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test workflows (LangGraph), API endpoints, database operations
- **Location**: All tests in `tests/` directory matching `test_*.py` pattern
- **Async tests**: Use `@pytest.mark.asyncio` decorator
- **Fixtures**: Reusable test data in `conftest.py`

## Reference Documentation

See dedicated CLAUDE.md files for detailed patterns:
- `api/CLAUDE.md`: FastAPI structure, service examples, endpoint development
- `open_notebook/CLAUDE.md`: Backend core, domain models, workflow orchestration
- `open_notebook/domain/CLAUDE.md`: Data models, repository pattern, search
- `open_notebook/ai/CLAUDE.md`: ModelManager, provider config, fallback logic
- `open_notebook/graphs/CLAUDE.md`: LangGraph design patterns, state machines
- `open_notebook/database/CLAUDE.md`: SurrealDB operations, migrations, async patterns
- `frontend/CLAUDE.md`: React/Next.js patterns, API integration, state management
- `README.md`: Project overview and features
- `README.dev.md`: Development environment setup and workflows
- `CONFIGURATION.md`: Environment variables and AI provider setup

## Support Resources

- **Discord**: https://discord.gg/37XJPXfz2w
- **GitHub Issues**: https://github.com/lfnovo/open-notebook/issues
- **Documentation**: https://open-notebook.ai
- **License**: MIT

---

**When in doubt about architecture or patterns**, check the relevant CLAUDE.md file in the component directory before asking questions.
