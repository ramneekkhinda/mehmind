# CI/CD Pipeline Documentation

## Overview

MeshMind uses GitHub Actions for continuous integration and deployment. The pipeline ensures code quality, security, and comprehensive testing across multiple Python versions.

## Workflows

### 1. Main Test Workflow (`.github/workflows/tests.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**
- **Test**: Runs on Python 3.11 and 3.12
  - Installs dependencies
  - Runs full test suite with coverage
  - Uploads coverage to Codecov
  - Runs unit and integration tests separately

- **Lint**: Code quality checks
  - `black` - Code formatting
  - `isort` - Import sorting
  - `flake8` - Style checking
  - `mypy` - Type checking

- **Security**: Security scanning
  - `bandit` - Security linting
  - `safety` - Dependency vulnerability scanning

### 2. Development Workflow (`.github/workflows/dev-tests.yml`)

**Triggers:**
- Daily at 2 AM UTC (scheduled)
- Manual workflow dispatch

**Features:**
- Manual test type selection (all, unit, integration, coverage, lint, security)
- Coverage artifact uploads
- Flexible testing options

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Count**: 28 tests
- **Purpose**: Fast, isolated tests for individual components
- **Examples**: Configuration, data structures, utility functions

### Integration Tests (`@pytest.mark.integration`)
- **Count**: 2 tests
- **Purpose**: Tests that interact with external systems
- **Examples**: File I/O, report saving

## Coverage Reporting

### Current Coverage
- **Overall**: 42%
- **Core Modules**: 100% (reports, init files)
- **Ghost-Run Simulator**: 52%
- **Ghost-Run Decorators**: 40%
- **CLI**: 22%

### Coverage Tools
- **pytest-cov**: Coverage collection
- **Codecov**: Coverage reporting and badges
- **HTML Reports**: Local coverage reports

## Local Testing

### Prerequisites
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Commands
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=meshmind --cov-report=term-missing

# Run specific categories
python -m pytest -m unit
python -m pytest -m integration

# Run specific files
python -m pytest tests/test_ghost_run.py
python -m pytest tests/test_ghost_reports.py
```

### Test Verification Script
```bash
# Run the CI verification script
chmod +x scripts/test-ci.sh
./scripts/test-ci.sh
```

## Code Quality Standards

### Formatting
- **black**: Code formatting (line length: 88)
- **isort**: Import sorting
- **flake8**: Style checking (with black compatibility)

### Type Checking
- **mypy**: Static type checking
- **Configuration**: Ignores missing imports, non-strict optional

### Security
- **bandit**: Security linting
- **safety**: Dependency vulnerability scanning

## Badges

The following badges are displayed in the README:

- **Tests**: ![Tests](https://github.com/ramneekkhinda/mehmind/workflows/Tests/badge.svg)
- **Coverage**: ![Coverage](https://codecov.io/gh/ramneekkhinda/mehmind/branch/main/graph/badge.svg)
- **Python**: ![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
- **License**: ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## Troubleshooting

### Common Issues

1. **Test Failures**
   - Check test output for specific error messages
   - Verify all dependencies are installed
   - Run tests locally before pushing

2. **Coverage Issues**
   - Ensure new code is covered by tests
   - Check for missing test files
   - Verify test markers are correctly applied

3. **Linting Failures**
   - Run `black` to format code
   - Run `isort` to sort imports
   - Fix flake8 warnings

4. **Security Issues**
   - Review bandit warnings
   - Update vulnerable dependencies
   - Check for security best practices

### Debugging

```bash
# Run tests with verbose output
python -m pytest -v

# Run tests with full traceback
python -m pytest --tb=long

# Run specific failing test
python -m pytest tests/test_ghost_run.py::TestGhostConfig::test_default_config -v

# Check test collection
python -m pytest --collect-only
```

## Future Enhancements

### Planned Improvements
- **Performance Testing**: Add performance benchmarks
- **Load Testing**: Test with large datasets
- **Docker Testing**: Test in containerized environments
- **Cross-Platform Testing**: Test on Windows, macOS, Linux

### Monitoring
- **Test Metrics**: Track test execution time
- **Coverage Trends**: Monitor coverage over time
- **Failure Analysis**: Track and analyze test failures

## Contributing

When contributing to MeshMind:

1. **Write Tests**: Ensure new features have corresponding tests
2. **Maintain Coverage**: Keep test coverage high
3. **Follow Standards**: Adhere to code quality standards
4. **Test Locally**: Run tests before submitting PRs
5. **Update Documentation**: Keep this document current
