# Test Strategy and Coverage Goals

## Overview

This document defines the testing strategy for the WireGuard Mesh Manager project,
including coverage goals for security-critical components and responsibilities
between unit, integration, and end-to-end tests.

## Current Testing Infrastructure

### Backend Testing Stack

- **Framework**: pytest with pytest-asyncio
- **Coverage**: pytest-cov with HTML and terminal reporting
- **Database**: Temporary in-memory SQLite for isolation
- **Test Count**: 51 test files covering API endpoints, services, and database models

### Frontend Testing Stack

- **Unit Tests**: Jest with React Testing Library (22 test files)
- **E2E Tests**: Playwright (6 test files)
- **Accessibility**: jest-axe for a11y testing
- **Coverage**: Built-in Jest coverage reporting

## Test Types and Responsibilities

### 1. Unit Tests

**Purpose**: Test individual functions, classes, and components in isolation

**Backend Unit Tests**:

- Service layer logic (encryption, key management, validation)
- Database model invariants and constraints
- Utility functions (CIDR validation, config generation)
- Schema validation and serialization/deserialization

**Frontend Unit Tests**:

- Component rendering and behavior
- Form validation and user interactions
- Utility functions and business logic
- State management and data transformations

### 2. Integration Tests

**Purpose**: Test interaction between multiple components or systems

**Backend Integration Tests**:

- API endpoint testing with temporary database
- Database migrations and constraint enforcement
- Cross-service workflows (device config generation, network export)
- Master-session authentication and authorization flows

**Frontend Integration Tests**:

- Component integration with mocked API responses
- Navigation and routing between pages
- Form submission flows and error handling

### 3. End-to-End Tests

**Purpose**: Test complete user workflows through the full application stack

**Current E2E Coverage**:

- Authentication flows (master password unlock/lock)
- CRUD operations for networks, locations, and devices
- Configuration export workflows
- Audit event viewing and filtering
- Advanced key rotation workflows

## Security-Critical Components and Coverage Goals

### High Security Priority (≥95% coverage)

#### Backend Components

| Component                      | Path                                    | Coverage | Critical Paths                                               | Test Focus                                       |
| ------------------------------ | --------------------------------------- | -------- | ------------------------------------------------------------ | ------------------------------------------------ |
| Encryption & Key Management    | `backend/app/utils/key_management.py`   | 100%     | Key generation, encryption/decryption, master password       | Edge cases, malformed input, boundary conditions |
| Device Configuration           | `backend/app/services/device_config.py` | 95%      | Private key decryption, config generation, data sanitization | Decrypted data security, error handling          |
| Authentication & Authorization | `backend/app/services/master_session.py` | 95%     | Session management, permission checking, API validation      | Bypass attempts, privilege escalation            |
| API Input Validation           | `backend/app/routers/`                  | 90%      | Request parsing, type validation, SQL injection prevention   | Malicious input, oversized payloads              |
| Database Constraints           | `backend/app/database/models.py`        | 95%      | Foreign keys, unique constraints, data integrity             | Constraint bypass, network isolation             |

#### Frontend Components

| Component               | Coverage | Critical Paths                                 | Test Focus                         |
| ----------------------- | -------- | ---------------------------------------------- | ---------------------------------- |
| Sensitive Data Handling | 90%      | Secure copy, data sanitization, memory cleanup | Data leakage prevention, redaction |
| Client-Side Validation  | 85%      | Input sanitization, error display              | XSS prevention, proper escaping    |

### Medium Security Priority (≥80% coverage)

| Component                   | Path                               | Critical Paths                                    | Test Focus                                  |
| --------------------------- | ---------------------------------- | ------------------------------------------------- | ------------------------------------------- |
| Audit & Logging             | `backend/app/services/audit.py`    | Event logging, data redaction, log integrity      | Redaction effectiveness, event completeness |
| Network & Device Management | `backend/app/services/networks.py` | Network isolation, IP allocation, device grouping | Cross-network access prevention             |
| Rate Limiting & Hardening   | `backend/app/middleware/`          | Request limits, timeouts, IP allowlists           | DoS prevention, abuse mitigation            |

### Standard Coverage (≥70% coverage)

- General business logic (CRUD, data transformation)
- Non-sensitive UI components
- Non-security-critical utilities

## Testing Best Practices

### Security Testing Guidelines

- **Malicious Input Testing**: Test malformed inputs, verify error handling without information leakage
- **Data Security**: Use test-only credentials, isolate test data, mock external dependencies, prevent data leakage
- **Edge Cases**: Test boundaries, Unicode handling, concurrent access, resource exhaustion
- **Authentication Boundaries**: Test bypass attempts, privilege escalation, master-session management

### Test Organization

1. **Test File Structure**:

   ```
   backend/tests/
   ├── test_security_critical.py      # Schema invariants, authZ, encryption
   ├── test_device_config_encryption.py  # Key management security
   ├── test_audit_integration.py      # Security logging
   ├── test_*.py                      # Other functional tests
   ```

2. **Test Naming Conventions**:

   - Security tests: `test_security_*`, `test_auth_*`, `test_encryption_*`
   - Integration tests: `test_*_integration.py`
   - E2E tests: `*.spec.ts` in `frontend/e2e/`

3. **Test Data Management**:
   - Use factories/fixtures for consistent test data creation
   - Clean up test data to prevent cross-test contamination
   - Use deterministic seeds for reproducible encryption tests

## Coverage Monitoring and Enforcement

### CI/CD Integration

1. **Coverage Thresholds** (enforced in CI):

   ```bash
   # Backend security files
   pytest --cov=app.utils.key_management --cov-fail-under=100
   pytest --cov=app.services.device_config --cov-fail-under=95
   pytest --cov=app.services.master_session --cov-fail-under=95

   # Overall backend coverage
   pytest --cov=app --cov-fail-under=80
   ```

2. **Coverage Reporting**:

   - HTML reports generated in CI for review
   - Coverage trends tracked over time
   - Security-critical file coverage highlighted in reports

3. **Quality Gates**:
   - Pull requests must maintain or improve coverage
   - Security-critical files have strict minimum coverage requirements
   - Coverage regression must be explicitly approved

## Current Coverage Analysis

### Backend Coverage Strengths

- Comprehensive security-focused test suite (`test_security_critical.py`)
- Strong encryption and key management testing
- Good coverage of database constraints and invariants
- Extensive audit logging tests

### Frontend Coverage Strengths

- Good E2E coverage for critical workflows
- Component-level testing for UI elements
- Accessibility testing integration

### Areas for Improvement

**Backend**:

- Enhanced error handling and edge case coverage
- More comprehensive API endpoint testing
- Better configuration validation edge cases

**Frontend**:

- Increased unit test coverage for security-critical components
- More integration testing with real API responses
- Enhanced error boundary testing

## Testing Documentation

Each test file should include:

- Clear purpose and scope documentation
- Security requirements being tested
- Test data specifications (especially for encryption tests)
- Coverage goals for the components under test

## Conclusion

This testing strategy provides a framework for maintaining high-quality, secure code
through comprehensive testing. Coverage goals ensure security-critical components
receive proper attention while maintaining overall system reliability.

Regular review and updates to this strategy should be performed as:

- New security threats are identified
- Application architecture evolves
- Testing tools and practices improve
- Regulatory requirements change
