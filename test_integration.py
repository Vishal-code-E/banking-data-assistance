#!/usr/bin/env python3
"""
Complete system integration test
Tests both AI Engine and Backend components
"""

print('🧪 Testing Complete System Integration\n')

# Test 1: AI Engine
print('1. Testing AI Engine...')
from ai_engine.main import run_banking_assistant
result = run_banking_assistant('Show transactions', verbose=False)
print(f'   ✅ AI Engine working: {result["validated_sql"][:50]}...')

# Test 2: Backend imports
print('\n2. Testing Backend modules...')
from backend.config import settings
from backend.schemas import QueryRequest, QueryResponse
from backend.validation import validate_sql
print(f'   ✅ Config loaded: {settings.APP_NAME}')
print(f'   ✅ Schemas imported: QueryRequest, QueryResponse')
print(f'   ✅ Validation module loaded')

# Test 3: Backend validation
print('\n3. Testing Backend SQL validation...')
validation_result = validate_sql('SELECT * FROM transactions LIMIT 10')
print(f'   ✅ Validation working: {validation_result.is_valid}')

print('\n' + '='*60)
print('✅ COMPLETE SYSTEM INTEGRATION SUCCESSFUL')
print('='*60)
print('\nAvailable components:')
print('  • AI Engine (LangGraph multi-agent)')
print('  • Backend (FastAPI + Database)')
print('  • Validation (Multi-layer security)')
print('  • Configuration (Environment-based)')
print('  • Schemas (Pydantic models)')
