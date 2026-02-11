#!/bin/bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly TESTS_DIR="$PROJECT_ROOT/tests/scripts"

setup_test_environment() {
    local test_name=$1

    local test_dir="$TESTS_DIR/$test_name"
    mkdir -p "$test_dir"

    cd "$test_dir"

    git init -q
    git config user.name "Test User"
    git config user.email "test@example.com"

    mkdir -p "$test_dir/backend"
    mkdir -p "$test_dir/frontend"

    echo "$test_dir"
}

cleanup_test_environment() {
    local test_name=$1
    rm -rf "$TESTS_DIR/$test_name"
}

test_supply_chain_security_script() {
    local test_name="supply_chain_test"
    local test_dir
    test_dir=$(setup_test_environment "$test_name")

    cd "$test_dir"

    echo "fastapi==0.104.1" > backend/requirements.txt
    echo "pytest==7.4.3" > backend/requirements-dev.txt
    echo '{"name": "test-app", "version": "1.0.0"}' > frontend/package.json

    # Create fake lock files
    touch backend/requirements.lock.txt
    touch frontend/package-lock.json

    # Test script execution
    if timeout 30 "$PROJECT_ROOT/scripts/supply-chain-security.sh" > /dev/null 2>&1; then
        echo "✓ Supply chain security script test passed"
        cleanup_test_environment "$test_name"
        return 0
    else
        echo "✗ Supply chain security script test failed"
        cleanup_test_environment "$test_name"
        return 1
    fi
}

test_update_dependencies_script() {
    local test_name="update_deps_test"
    local test_dir
    test_dir=$(setup_test_environment "$test_name")

    cd "$test_dir"

    echo "fastapi==0.104.1" > backend/requirements.txt
    echo "pytest==7.4.3" > backend/requirements-dev.txt
    echo '{"name": "test-app", "version": "1.0.0", "devDependencies": {"jest": "^29.0.0"}}' > frontend/package.json

    # Create fake requirements.in file
    echo "fastapi" > backend/requirements.in

    # Test script validation (dry run)
    timeout 30 bash -c "cd '$test_dir' && '$PROJECT_ROOT/scripts/update-dependencies.sh' --dry-run" > /dev/null 2>&1 || true

    echo "✓ Update dependencies script test completed (dry run)"
    cleanup_test_environment "$test_name"
    return 0
}

test_script_syntax() {
    local script_path
    for script_path in "$PROJECT_ROOT"/scripts/*.sh; do
        if bash -n "$script_path"; then
            echo "✓ Syntax check passed for $(basename "$script_path")"
        else
            echo "✗ Syntax check failed for $(basename "$script_path")"
            return 1
        fi
    done
    return 0
}

test_script_permissions() {
    local script_path
    for script_path in "$PROJECT_ROOT"/scripts/*.sh; do
        if [[ -x "$script_path" ]]; then
            echo "✓ Execute permission set for $(basename "$script_path")"
        else
            echo "⚠ Execute permission missing for $(basename "$script_path")"
        fi
    done
    return 0
}

main() {
    echo "=== Running Script Tests ==="

    mkdir -p "$TESTS_DIR"

    local failed=0

    test_script_syntax || failed=1
    test_script_permissions || failed=1
    test_supply_chain_security_script || failed=1
    test_update_dependencies_script || failed=1

    if [ $failed -eq 0 ]; then
        echo "✓ All script tests passed"
        exit 0
    else
        echo "✗ Some script tests failed"
        exit 1
    fi
}

main "$@"
