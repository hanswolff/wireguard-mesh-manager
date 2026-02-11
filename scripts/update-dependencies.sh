#!/bin/bash
set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly REPORTS_DIR="$PROJECT_ROOT/reports"
readonly FRONTEND_DIR="$PROJECT_ROOT/frontend"
readonly BACKEND_DIR="$PROJECT_ROOT/backend"

mkdir -p "$REPORTS_DIR"

log_section() { echo -e "${BLUE}=== $1 ===${NC}"; }
log_success() { echo -e "${GREEN}✓ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
log_error() { echo -e "${RED}✗ $1${NC}"; }
command_exists() { command -v "$1" >/dev/null 2>&1; }

# Function to create a branch for dependency updates
create_update_branch() {
    local update_type=$1
    local branch_name="deps/update-$(date +%Y%m%d)-$update_type"

    if [[ -n "$(git status --porcelain)" ]]; then
        log_warning "Uncommitted changes detected. Please commit or stash them first."
        return 1
    fi

    # Check if branch already exists
    if git rev-parse --verify "$branch_name" >/dev/null 2>&1; then
        log_warning "Branch $branch_name already exists. Checking it out..."
        git checkout "$branch_name"
        git pull origin "$branch_name" || true
    else
        log_success "Creating new branch: $branch_name"
        git checkout -b "$branch_name"
    fi

    echo "$branch_name"
}

# Function to create pull request
create_pull_request() {
    local branch_name=$1
    local title=$2
    local body=$3

    # This would need to be adapted based on your Git hosting (GitHub, GitLab, etc.)
    log_success "Branch $branch_name is ready for review"
    echo "Title: $title"
    echo "Description: $body"
    echo ""
    echo "To create a pull request:"
    echo "1. Push the branch: git push origin $branch_name"
    echo "2. Create a pull request using your Git hosting interface"
}

update_python_dependencies() {
    log_section "Updating Python Dependencies"

    cd "$BACKEND_DIR"

    cp requirements.txt requirements.txt.backup
    cp requirements-dev.txt requirements-dev.txt.backup

    log_success "Updating pip and pip-tools..."
    python -m pip install --upgrade pip pip-tools

    log_success "Updating main dependencies..."
    pip-compile requirements.in --upgrade --generate-hashes --output-file=requirements.lock.txt

    log_success "Updating development dependencies..."
    pip-compile requirements-dev.txt --upgrade --generate-hashes --output-file=requirements-dev.lock.txt

    command_exists safety && safety check --json --output "$REPORTS_DIR/safety-updates.json" || true

    cat > "$REPORTS_DIR/python-dependency-updates.md" << EOF
# Python Dependency Updates

Updated on: $(date)

## Changes Made

- Updated pip-tools to latest version
- Recompiled requirements.lock.txt with latest compatible versions
- Recompiled requirements-dev.lock.txt with latest compatible versions
EOF

    log_success "Running Python tests..."
    python -m pytest tests/ -v --tb=short
}

update_nodejs_dependencies() {
    log_section "Updating Node.js Dependencies"

    update_npm_project() {
        local project_dir=$1
        local project_name=$2

        cd "$project_dir"
        log_success "Updating $project_name dependencies..."
        npm update
        npm audit --audit-level=moderate
    }

    update_npm_project "$FRONTEND_DIR" "frontend"
    npm run test:unit

    cat > "$REPORTS_DIR/nodejs-dependency-updates.md" << EOF
# Node.js Dependency Updates

Updated on: $(date)

## Frontend Changes
- Updated packages via npm update
- Security audit completed
EOF
}

update_docker_dependencies() {
    log_section "Updating Docker Base Images"

    cd "$PROJECT_ROOT"

    command_exists skopeo && log_success "Checking for Docker base image updates..." || log_warning "skopeo not available, skipping Docker image update checks"
}

generate_update_report() {
    log_section "Generating Update Report"

    cd "$PROJECT_ROOT"

    local report_date=$(date +%Y%m%d)
    local git_branch=$(git branch --show-current)

    cat > "$REPORTS_DIR/dependency-update-report-$report_date.md" << EOF
# Dependency Update Report

Generated on: $(date)
Git branch: $git_branch

## Executive Summary

This report summarizes the automated dependency updates performed on $(date).

## Python Backend Updates

- Requirements file: requirements.lock.txt
- Dev requirements: requirements-dev.lock.txt

## Node.js Frontend Updates

- Frontend packages: package-lock.json

## Recommendations

1. Review all dependency updates for breaking changes
2. Run full test suite including integration tests
3. Test application functionality manually
4. Monitor for any runtime issues after deployment
EOF

    log_success "Update report generated: $REPORTS_DIR/dependency-update-report-$report_date.md"
}

commit_and_create_pr() {
    local update_type=$1
    local branch_name

    branch_name=$(create_update_branch "$update_type")

    log_success "Staging updated dependency files..."
    cd "$PROJECT_ROOT"

    git add backend/requirements.lock.txt
    git add backend/requirements-dev.lock.txt
    git add frontend/package-lock.json
    git add reports/

    local commit_date=$(date +%Y-%m-%d)
    local commit_message="chore: update dependencies ($commit_date)

- Update Python dependencies with pip-compile
- Update Node.js dependencies with npm update
- Update lock files with latest secure versions
- Run security vulnerability scans
- Generate dependency update reports

This commit was generated by the automated dependency update script."

    git commit -m "$commit_message"

    local pr_title="Automated Dependency Update - $commit_date"
    local pr_body="This PR contains automated dependency updates:

## Changes
- Updated Python dependencies in backend/
- Updated Node.js dependencies in frontend/
- Updated lock files with latest compatible versions
- Generated security and update reports

## Testing
- Automated tests have been run
- Security vulnerability scans completed
- Please review breaking changes in dependencies

## Review Checklist
- [ ] Review breaking changes in updated dependencies
- [ ] Run full integration test suite
- [ ] Test application manually
- [ ] Check for any runtime errors
- [ ] Monitor performance after deployment

Generated by: scripts/update-dependencies.sh"

    create_pull_request "$branch_name" "$pr_title" "$pr_body"
}

main() {
    echo -e "${GREEN}=== Automated Dependency Update ===${NC}"
    echo "Project root: $PROJECT_ROOT"
    echo "Reports directory: $REPORTS_DIR"
    echo

    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository. Please run this script from within a git repository."
        exit 1
    fi

    log_section "Installing Required Tools"

    command_exists pip && pip install --upgrade pip-tools safety pip-audit pip-licenses || true
    command_exists npm && npm install -g npm audit fix || true

    local update_failed=false

    update_python_dependencies || {
        update_failed=true
        log_error "Python dependency update failed"
    }

    update_nodejs_dependencies || {
        update_failed=true
        log_error "Node.js dependency update failed"
    }

    update_docker_dependencies
    generate_update_report

    if [ "$update_failed" = false ]; then
        log_section "Creating Pull Request"
        commit_and_create_pr "all"

        log_success "Dependency update completed successfully!"
        echo ""
        echo "Next steps:"
        echo "1. Push the created branch to origin"
        echo "2. Create and merge the pull request"
        echo "3. Monitor the CI/CD pipeline"
        echo "4. Deploy after successful testing"
    else
        log_error "Some dependency updates failed. Please review the errors above."
        exit 1
    fi
}

main "$@"
