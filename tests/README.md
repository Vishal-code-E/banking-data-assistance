# Test Suite Documentation

## Banking Data Assistant - Comprehensive Test Suite

This directory contains a comprehensive test suite for the AI Banking Data Assistant, covering all phases from functional tests to integration tests.

## Test Structure

```
tests/
├── conftest.py                    # pytest configuration and fixtures
├── test_phase1_functional.py      # Valid query tests
├── test_phase2_security.py        # Security and injection tests
├── test_phase3_agent_logic.py     # Agent behavior tests
├── test_phase4_edge_cases.py      # Edge cases and error handling
└── test_phase5_integration.py     # End-to-end integration tests
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Phase
```bash
# Phase 1: Functional tests
pytest tests/test_phase1_functional.py -v

# Phase 2: Security tests
pytest tests/test_phase2_security.py -v

# Phase 3: Agent logic tests
pytest tests/test_phase3_agent_logic.py -v

# Phase 4: Edge cases
pytest tests/test_phase4_edge_cases.py -v

# Phase 5: Integration tests
pytest tests/test_phase5_integration.py -v
```

### Run by Marker
```bash
# Run only security tests
pytest -m security -v

# Run only integration tests
pytest -m integration -v

# Run only AI agent tests
pytest -m ai -v

# Skip slow tests
pytest -m "not slow" -v
```

### Run with Coverage
```bash
pytest tests/ --cov=backend --cov=ai_engine --cov-report=html
```

### Run Specific Test
```bash
pytest tests/test_phase1_functional.py::TestValidQueries::test_simple_transaction_query -v
```

## Test Phases

### Phase 1: Functional Tests (Valid Queries)
**File**: `test_phase1_functional.py`

Tests valid banking queries:
- ✅ Simple transaction queries
- ✅ High-value transaction filters
- ✅ Customer account JOINs
- ✅ Daily credit summaries
- ✅ Account balance queries
- ✅ Complex aggregations
- ✅ Output structure validation

**Coverage**:
- SQL pattern validation
- JSON output structure
- Summary generation
- Chart suggestions

### Phase 2: Security Tests (SQL Injection)
**File**: `test_phase2_security.py`

Tests protection against malicious inputs:
- ✅ Stacked queries (`; DROP TABLE`)
- ✅ Comment-based injection (`--`)
- ✅ UNION-based injection
- ✅ Tautology attacks (`OR 1=1`)
- ✅ System table access
- ✅ Dangerous keyword blocking (INSERT, UPDATE, DELETE, DROP, ALTER)
- ✅ Table whitelist enforcement

**Expected Behavior**:
- Validation agent blocks query
- Error returned to user
- No execution occurs
- Database remains safe

### Phase 3: Agent Logic Tests
**File**: `test_phase3_agent_logic.py`

Tests agent behavior and workflow:
- ✅ Retry logic on invalid SQL
- ✅ Max retry limit enforcement
- ✅ Successful retry recovery
- ✅ Intent classification
- ✅ Ambiguous query handling
- ✅ Validation agent blocking
- ✅ Insight generation
- ✅ Chart suggestion appropriateness
- ✅ State management and flow

**Agent Coverage**:
- Intent Agent
- SQL Agent
- Validation Agent
- Insight Agent

### Phase 4: Edge Cases
**File**: `test_phase4_edge_cases.py`

Tests boundary conditions:
- ✅ Empty queries
- ✅ Whitespace-only queries
- ✅ Very long queries (>1000 chars)
- ✅ Special characters
- ✅ Unicode characters
- ✅ Large result sets (>1000 rows)
- ✅ No results scenarios
- ✅ Non-existent tables
- ✅ Table name typos
- ✅ Nonsensical input
- ✅ Malformed state
- ✅ Graceful degradation

**Expected Behavior**:
- No crashes
- Proper error messages
- Graceful handling
- User-friendly errors

### Phase 5: Integration Tests
**File**: `test_phase5_integration.py`

Tests complete pipeline:
- ✅ Backend API endpoints (`/health`, `/query`, `/tables`)
- ✅ End-to-end query processing
- ✅ Output contract validation
- ✅ Realistic user scenarios
- ✅ Performance testing
- ✅ Concurrent request handling

**Pipeline Flow**:
```
User Query → Intent Agent → SQL Agent → Validation Agent → Backend Execution → Insight Agent → Response
```

**Output Contract**:
```json
{
  "validated_sql": "SELECT ...",
  "summary": "Found 5 transactions...",
  "chart_suggestion": "bar",
  "error_message": null
}
```

## Test Coverage Metrics

### Expected Coverage
- Backend: >80%
- AI Engine: >75%
- Integration: >70%

### Key Areas Covered
1. **Security**: 100% (critical)
2. **Validation**: 100% (critical)
3. **Execution**: 95%
4. **Agents**: 80%
5. **API Endpoints**: 100%

## Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx pytest-cov

# Ensure database is initialized
python -c "from backend.db import init_database; init_database()"
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pytest tests/ -v --cov=backend --cov=ai_engine
```

## Test Data

Tests use the seed data from `models/schema.sql`:
- 5 customers
- 7 accounts
- 24 transactions

## Mocking

Some tests use mocking for:
- LLM API calls (to avoid API costs)
- External dependencies
- Error simulation

## Debugging Failed Tests

```bash
# Run with detailed output
pytest tests/ -vv -s

# Run specific failing test
pytest tests/test_phase2_security.py::TestSQLInjectionPrevention::test_stacked_queries_attack -vv -s

# Drop into debugger on failure
pytest tests/ --pdb

# Show local variables on failure
pytest tests/ -l
```

## Performance Benchmarks

Expected performance:
- Simple query: <100ms
- Complex query: <500ms
- AI pipeline: <2s (without LLM)
- With LLM: <5s

## Security Test Checklist

- [ ] SQL injection patterns blocked
- [ ] Dangerous keywords rejected
- [ ] Table whitelist enforced
- [ ] Comment injection prevented
- [ ] Multi-statement queries blocked
- [ ] System table access denied
- [ ] Only SELECT allowed

## Contributing

When adding new features:
1. Add functional tests (Phase 1)
2. Add security tests if applicable (Phase 2)
3. Add edge case tests (Phase 4)
4. Add integration tests (Phase 5)
5. Ensure >80% coverage

## Known Issues

None at this time.

## Contact

For test-related questions, see main README.
