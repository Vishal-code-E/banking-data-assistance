#!/bin/bash
# Test runner script for Banking Data Assistant

echo "========================================="
echo "Banking Data Assistant - Test Suite"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest not found. Installing...${NC}"
    pip install pytest pytest-asyncio httpx pytest-cov
fi

# Function to run tests
run_tests() {
    local phase=$1
    local file=$2
    
    echo -e "${YELLOW}Running $phase...${NC}"
    pytest "$file" -v
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $phase PASSED${NC}"
    else
        echo -e "${RED}✗ $phase FAILED${NC}"
        return 1
    fi
    echo ""
}

# Parse arguments
case "$1" in
    --phase1)
        run_tests "Phase 1: Functional Tests" "tests/test_phase1_functional.py"
        ;;
    --phase2)
        run_tests "Phase 2: Security Tests" "tests/test_phase2_security.py"
        ;;
    --phase3)
        run_tests "Phase 3: Agent Logic Tests" "tests/test_phase3_agent_logic.py"
        ;;
    --phase4)
        run_tests "Phase 4: Edge Cases" "tests/test_phase4_edge_cases.py"
        ;;
    --phase5)
        run_tests "Phase 5: Integration Tests" "tests/test_phase5_integration.py"
        ;;
    --security)
        echo -e "${YELLOW}Running Security Tests Only...${NC}"
        pytest tests/test_phase2_security.py -v -m security
        ;;
    --integration)
        echo -e "${YELLOW}Running Integration Tests Only...${NC}"
        pytest tests/test_phase5_integration.py -v -m integration
        ;;
    --coverage)
        echo -e "${YELLOW}Running All Tests with Coverage...${NC}"
        pytest tests/ -v --cov=backend --cov=ai_engine --cov-report=html --cov-report=term
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    --quick)
        echo -e "${YELLOW}Running Quick Tests (excluding slow tests)...${NC}"
        pytest tests/ -v -m "not slow"
        ;;
    --all|"")
        echo -e "${YELLOW}Running All Test Phases...${NC}"
        echo ""
        
        run_tests "Phase 1: Functional Tests" "tests/test_phase1_functional.py" && \
        run_tests "Phase 2: Security Tests" "tests/test_phase2_security.py" && \
        run_tests "Phase 3: Agent Logic Tests" "tests/test_phase3_agent_logic.py" && \
        run_tests "Phase 4: Edge Cases" "tests/test_phase4_edge_cases.py" && \
        run_tests "Phase 5: Integration Tests" "tests/test_phase5_integration.py"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}=========================================${NC}"
            echo -e "${GREEN}All Test Phases PASSED ✓${NC}"
            echo -e "${GREEN}=========================================${NC}"
        else
            echo -e "${RED}=========================================${NC}"
            echo -e "${RED}Some Tests FAILED ✗${NC}"
            echo -e "${RED}=========================================${NC}"
            exit 1
        fi
        ;;
    --help)
        echo "Usage: ./run_tests.sh [option]"
        echo ""
        echo "Options:"
        echo "  --all          Run all test phases (default)"
        echo "  --phase1       Run Phase 1: Functional Tests"
        echo "  --phase2       Run Phase 2: Security Tests"
        echo "  --phase3       Run Phase 3: Agent Logic Tests"
        echo "  --phase4       Run Phase 4: Edge Cases"
        echo "  --phase5       Run Phase 5: Integration Tests"
        echo "  --security     Run security tests only"
        echo "  --integration  Run integration tests only"
        echo "  --coverage     Run with coverage report"
        echo "  --quick        Run quick tests (skip slow tests)"
        echo "  --help         Show this help message"
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
