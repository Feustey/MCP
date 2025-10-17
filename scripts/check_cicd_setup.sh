#!/bin/bash
################################################################################
# Script de vérification de la configuration CI/CD
#
# Ce script vérifie que tous les prérequis pour le CI/CD sont en place
#
# Usage: ./scripts/check_cicd_setup.sh
#
# Auteur: MCP Team
# Date: 17 octobre 2025
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
}

check_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    CHECKS_WARNING=$((CHECKS_WARNING + 1))
}

# Banner
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║         ${GREEN}CI/CD Setup Verification - MCP${NC}                   ${BLUE}║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check 1: Workflows files
print_header "1. GitHub Workflows"

if [ -f ".github/workflows/deploy-production.yml" ]; then
    check_pass "deploy-production.yml exists"
else
    check_fail "deploy-production.yml missing"
fi

if [ -f ".github/workflows/tests.yml" ]; then
    check_pass "tests.yml exists"
else
    check_fail "tests.yml missing"
fi

if [ -f ".github/workflows/rollback.yml" ]; then
    check_pass "rollback.yml exists"
else
    check_fail "rollback.yml missing"
fi

# Check 2: Scripts
print_header "2. Deployment Scripts"

if [ -f "scripts/ci_deploy.sh" ]; then
    check_pass "ci_deploy.sh exists"
    if [ -x "scripts/ci_deploy.sh" ]; then
        check_pass "ci_deploy.sh is executable"
    else
        check_warning "ci_deploy.sh is not executable (run: chmod +x scripts/ci_deploy.sh)"
    fi
else
    check_fail "ci_deploy.sh missing"
fi

# Check 3: Docker files
print_header "3. Docker Configuration"

if [ -f "docker-compose.production.yml" ]; then
    check_pass "docker-compose.production.yml exists"
    
    # Validate docker-compose syntax
    if command -v docker-compose &> /dev/null; then
        if docker-compose -f docker-compose.production.yml config > /dev/null 2>&1; then
            check_pass "docker-compose.production.yml syntax is valid"
        else
            check_fail "docker-compose.production.yml has syntax errors"
        fi
    else
        check_warning "docker-compose not installed, cannot validate syntax"
    fi
else
    check_fail "docker-compose.production.yml missing"
fi

if [ -f "Dockerfile.production" ]; then
    check_pass "Dockerfile.production exists"
else
    check_fail "Dockerfile.production missing"
fi

# Check 4: Documentation
print_header "4. Documentation"

if [ -f "docs/CICD_SETUP.md" ]; then
    check_pass "CICD_SETUP.md exists"
else
    check_fail "CICD_SETUP.md missing"
fi

if [ -f "CICD_QUICKSTART.md" ]; then
    check_pass "CICD_QUICKSTART.md exists"
else
    check_fail "CICD_QUICKSTART.md missing"
fi

if [ -f "docs/DEPLOYMENT_RUNBOOK.md" ]; then
    check_pass "DEPLOYMENT_RUNBOOK.md exists"
else
    check_fail "DEPLOYMENT_RUNBOOK.md missing"
fi

# Check 5: Configuration files
print_header "5. Configuration Files"

if [ -f ".gitignore" ]; then
    check_pass ".gitignore exists"
    
    if grep -q "deploy-package.tar.gz" .gitignore; then
        check_pass ".gitignore includes CI/CD artifacts"
    else
        check_warning ".gitignore should include CI/CD artifacts"
    fi
else
    check_fail ".gitignore missing"
fi

# Check 6: Git configuration
print_header "6. Git Configuration"

if git rev-parse --git-dir > /dev/null 2>&1; then
    check_pass "Git repository initialized"
    
    if git remote get-url origin > /dev/null 2>&1; then
        REMOTE_URL=$(git remote get-url origin)
        check_pass "Git remote configured: $REMOTE_URL"
        
        if [[ $REMOTE_URL == *"github.com"* ]]; then
            check_pass "Remote is GitHub (CI/CD compatible)"
        else
            check_warning "Remote is not GitHub, GitHub Actions won't work"
        fi
    else
        check_fail "No git remote configured"
    fi
else
    check_fail "Not a git repository"
fi

# Check 7: GitHub-specific files
print_header "7. GitHub Templates"

if [ -f ".github/PULL_REQUEST_TEMPLATE.md" ]; then
    check_pass "Pull Request template exists"
else
    check_warning "Pull Request template missing (recommended)"
fi

if [ -f ".github/ISSUE_TEMPLATE/deployment_issue.md" ]; then
    check_pass "Deployment issue template exists"
else
    check_warning "Deployment issue template missing (recommended)"
fi

# Check 8: Dependencies
print_header "8. Python Dependencies"

if [ -f "requirements-production.txt" ]; then
    check_pass "requirements-production.txt exists"
else
    check_fail "requirements-production.txt missing"
fi

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    check_pass "Python installed: $PYTHON_VERSION"
    
    if [[ $PYTHON_VERSION == 3.9* ]] || [[ $PYTHON_VERSION == 3.10* ]]; then
        check_pass "Python version compatible (3.9+)"
    else
        check_warning "Python version may not be compatible (recommend 3.9 or 3.10)"
    fi
else
    check_warning "Python3 not found in PATH"
fi

# Check 9: Environment file
print_header "9. Environment Configuration"

if [ -f "config_production_hostinger.env" ]; then
    check_pass "config_production_hostinger.env exists (template)"
else
    check_warning "config_production_hostinger.env missing (template for server)"
fi

if [ -f ".env.production" ]; then
    check_warning ".env.production exists locally (should only be on server)"
else
    check_pass ".env.production not in local repository (correct)"
fi

# Check 10: Server-specific checks (if SSH config available)
print_header "10. Server Connection (Optional)"

if [ -n "${HOSTINGER_HOST:-}" ]; then
    echo "Testing connection to ${HOSTINGER_HOST}..."
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "${HOSTINGER_USER:-root}@${HOSTINGER_HOST}" "echo 'OK'" 2>/dev/null; then
        check_pass "Can connect to server"
    else
        check_warning "Cannot connect to server (normal if not configured yet)"
    fi
else
    check_warning "HOSTINGER_HOST not set (set for server checks)"
fi

# Summary
print_header "Summary"

TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNING))

echo ""
echo -e "Total checks: ${BLUE}$TOTAL_CHECKS${NC}"
echo -e "  ${GREEN}✓ Passed:   $CHECKS_PASSED${NC}"
echo -e "  ${RED}✗ Failed:   $CHECKS_FAILED${NC}"
echo -e "  ${YELLOW}⚠ Warnings: $CHECKS_WARNING${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ CI/CD setup is complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Configure GitHub secrets (see docs/CICD_SETUP.md)"
    echo "2. Setup SSH key on server (see CICD_QUICKSTART.md)"
    echo "3. Test with: git push origin main"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ CI/CD setup has issues${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Please fix the failed checks above."
    echo "See documentation: docs/CICD_SETUP.md"
    echo ""
    exit 1
fi

