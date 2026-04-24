#!/bin/bash
# Test runner script for DeerTeamX authentication module unit tests
# Usage: ./run_auth_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
VERBOSE=false
COVERAGE=false
HTML_REPORT=false
SPECIFIC_TEST=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -h|--html)
            HTML_REPORT=true
            shift
            ;;
        -t|--test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose     Enable verbose output"
            echo "  -c, --coverage    Run with coverage report"
            echo "  -h, --html        Generate HTML coverage report"
            echo "  -t, --test TEST   Run specific test (e.g., 'TestJWTToken::test_create_access_token_returns_valid_jwt')"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Change to backend directory
cd "$(dirname "$0")/../.."

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DeerTeamX Auth Module Unit Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Virtual environment not detected.${NC}"
    echo -e "${YELLOW}Make sure pytest and dependencies are installed.${NC}"
    echo ""
fi

# Build pytest command
PYTEST_CMD="pytest tests/deerteamx/test_auth_unit.py"

# Add verbosity
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v -s"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add specific test
if [ -n "$SPECIFIC_TEST" ]; then
    PYTEST_CMD="$PYTEST_CMD::$SPECIFIC_TEST"
fi

# Add coverage options
if [ "$COVERAGE" = true ] || [ "$HTML_REPORT" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=deerteamx.api.routers.auth"
    PYTEST_CMD="$PYTEST_CMD --cov=deerteamx.api.middleware.auth"
    PYTEST_CMD="$PYTEST_CMD --cov=deerteamx.api.dependencies"
    PYTEST_CMD="$PYTEST_CMD --cov=deerteamx.models.base"
    PYTEST_CMD="$PYTEST_CMD --cov-report=term-missing"
    
    if [ "$HTML_REPORT" = true ]; then
        PYTEST_CMD="$PYTEST_CMD --cov-report=html:htmlcov/auth_coverage"
    fi
fi

# Run tests
echo -e "${BLUE}Running: ${PYTEST_CMD}${NC}"
echo ""

if eval "$PYTEST_CMD"; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Show coverage summary if enabled
    if [ "$HTML_REPORT" = true ]; then
        echo ""
        echo -e "${BLUE}HTML coverage report generated:${NC}"
        echo -e "${BLUE}  file://$(pwd)/htmlcov/auth_coverage/index.html${NC}"
        echo ""
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Some tests failed!${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
