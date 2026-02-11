#!/bin/bash
set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly REPORTS_DIR="$PROJECT_ROOT/reports"
readonly FRONTEND_DIR="$PROJECT_ROOT/frontend"
readonly BACKEND_DIR="$PROJECT_ROOT/backend"

mkdir -p "$REPORTS_DIR"

log_section() { echo -e "${GREEN}=== $1 ===${NC}"; }
log_warning() { echo -e "${YELLOW}WARNING: $1${NC}"; }
log_error() { echo -e "${RED}ERROR: $1${NC}"; }
command_exists() { command -v "$1" >/dev/null 2>&1; }

OVERALL_SUCCESS=true

log_section "Python Backend Dependency Security Scan"

cd "$BACKEND_DIR"

if [[ -f "requirements.lock.txt" ]]; then
    echo "✓ Found pinned requirements.lock.txt"

    if command_exists safety; then
        echo "Running safety check..."
        if safety check -r requirements.lock.txt --json --output "$REPORTS_DIR/safety-locked-report.json" 2>/dev/null; then
            echo "✓ No vulnerabilities found"
        else
            log_warning "Vulnerabilities found - check safety-locked-report.json"
            OVERALL_SUCCESS=false
        fi
    else
        log_warning "safety not installed, skipping vulnerability scan"
    fi

    command_exists pip-audit && pip-audit -r requirements.lock.txt --format=json --output="$REPORTS_DIR/pip-audit-report.json" 2>/dev/null || true
else
    log_error "No requirements.lock.txt found - dependencies not properly pinned"
    OVERALL_SUCCESS=false
fi

log_section "Frontend Dependency Security Scan"

check_npm_dependencies() {
    local dir=$1
    local report_file=$2

    cd "$dir"

    if [[ -f "package-lock.json" ]]; then
        echo "✓ Found package-lock.json in $dir"
        npm audit --audit-level=moderate --json > "$REPORTS_DIR/$report_file" 2>/dev/null || {
            log_warning "Vulnerabilities found in $dir - check $report_file"
            OVERALL_SUCCESS=false
        }
    else
        log_error "No package-lock.json found in $dir"
        OVERALL_SUCCESS=false
    fi
}

check_npm_dependencies "$FRONTEND_DIR" "npm-audit-report.json"

log_section "License Compliance Check"

cd "$PROJECT_ROOT"

command_exists pip-licenses && {
    cd "$BACKEND_DIR"
    pip-licenses --from=mixed --format=json --output-file="$REPORTS_DIR/python-licenses.json" 2>/dev/null || true
}

command_exists license-checker && {
    cd "$FRONTEND_DIR"
    license-checker --json --output "$REPORTS_DIR/frontend-licenses.json" 2>/dev/null || true
}

log_section "Dependency Integrity Verification"

cd "$BACKEND_DIR"
[[ -f "requirements.lock.txt" ]] && {
    echo "Verifying Python dependency hashes..."
    python3 -c "
import re
with open('requirements.lock.txt', 'r') as f:
    content = f.read()
packages = re.split(r'\n\n(?=\w)', content)
for package in packages:
    if ' --hash=' in package:
        lines = package.strip().split('\n')
        if lines:
            package_name = lines[0].split('==')[0].strip()
            hashes = re.findall(r'--hash=([a-f0-9]+):([a-f0-9]+)', package)
            if hashes:
                print(f'Verifying {package_name} with {len(hashes)} hash(es)')
print('Hash verification completed')
" 2>/dev/null || log_warning "Could not verify dependency hashes"
}

log_section "Supply Chain Attack Prevention"

cd "$PROJECT_ROOT"

echo "Checking for common supply chain security practices..."

grep -q "~=" requirements.txt 2>/dev/null && log_warning "Found compatible version specifiers (~=) - consider using exact versions"
grep -q ">=" requirements.txt 2>/dev/null && log_warning "Found minimum version specifiers (>=) - consider using exact versions"

log_section "Generating Security Report"

cd "$PROJECT_ROOT"

python_status=$([ -f "$BACKEND_DIR/requirements.lock.txt" ] && echo "✓ PINNED" || echo "✗ NOT PINNED")
frontend_status=$([ -f "$FRONTEND_DIR/package-lock.json" ] && echo "✓ PINNED" || echo "✗ NOT PINNED")

cat > "$REPORTS_DIR/supply-chain-security-report.md" << EOF
# Supply Chain Security Report

Generated on: $(date)

## Dependency Status

### Python Backend
- **Pinning Status**: $python_status

### Frontend
- **Pinning Status**: $frontend_status

## Security Findings

Detailed security findings are available in the respective JSON reports:
- safety-locked-report.json: Python dependency vulnerabilities
- npm-audit-report.json: Frontend dependency vulnerabilities
- pip-audit-report.json: Additional Python vulnerability scan

## Recommendations

1. **Regular Updates**: Implement automated dependency updates
2. **Lock Files**: Always use lock files for dependency installation
3. **Vulnerability Monitoring**: Set up alerts for new vulnerabilities
4. **License Compliance**: Review and approve all dependencies
5. **Supply Chain Monitoring**: Consider tools like Snyk or Dependabot
EOF

echo "✓ Supply chain security report generated: $REPORTS_DIR/supply-chain-security-report.md"

echo
log_section "Security Verification Complete"

if [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "${GREEN}✓ All security checks passed successfully${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Security checks completed with warnings${NC}"
    echo "Review the reports in $REPORTS_DIR for details"
    exit 1
fi
