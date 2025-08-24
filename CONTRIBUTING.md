# Contributing to MeshMind

Thank you for your interest in contributing to MeshMind! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Docker and Docker Compose (for local development)

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/meshmind.git
   cd meshmind
   ```

2. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Setup pre-commit hooks**
   ```bash
   pre-commit install
   ```

4. **Start local services**
   ```bash
   docker-compose up -d
   ```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=meshmind

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m slow

# Run tests in parallel
pytest -n auto
```

### Test Categories

- **Unit tests** (`-m unit`): Fast, isolated tests
- **Integration tests** (`-m integration`): Tests requiring external services
- **Slow tests** (`-m slow`): Tests that take longer to run

## 📝 Code Quality

### Code Formatting

We use automated tools to maintain code quality:

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
ruff check src/
ruff check src/ --fix
```

### Pre-commit Hooks

Pre-commit hooks automatically run on every commit:

- Code formatting (black, isort)
- Linting (ruff)
- Type checking (mypy)
- Test execution

## 🏗️ Project Structure

```
meshmind/
├── src/meshmind/          # Main package
│   ├── core/             # Core functionality
│   ├── langgraph/        # LangGraph integration
│   └── utils/            # Utilities
├── referee/              # Referee service
├── examples/             # Example applications
├── tests/                # Test suite
└── docs/                 # Documentation
```

## 📋 Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding standards
   - Add tests for new functionality
   - Update documentation if needed

3. **Run quality checks**
   ```bash
   # Format and lint
   black src/
   isort src/
   ruff check src/

   # Type check
   mypy src/

   # Run tests
   pytest
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

## 🐛 Reporting Issues

When reporting issues, please include:

1. **Environment information**
   - Python version
   - Operating system
   - MeshMind version

2. **Steps to reproduce**
   - Clear, step-by-step instructions
   - Minimal code example

3. **Expected vs actual behavior**
   - What you expected to happen
   - What actually happened

4. **Additional context**
   - Error messages and stack traces
   - Logs (if applicable)

## 📚 Documentation

### Adding Documentation

1. **Code documentation**: Use docstrings for all public APIs
2. **README updates**: Update README.md for user-facing changes
3. **API documentation**: Update docstrings and examples

### Documentation Standards

- Use clear, concise language
- Include code examples
- Follow the existing style
- Test all code examples

## 🔧 Development Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all function parameters and return values
- Write descriptive variable and function names
- Add docstrings for all public functions and classes

### Error Handling

- Use custom exception classes from `meshmind.utils.errors`
- Provide meaningful error messages
- Include structured data in error objects
- Log errors with appropriate levels

### Testing

- Write tests for all new functionality
- Aim for high test coverage
- Use descriptive test names
- Mock external dependencies
- Test both success and failure cases

### Performance

- Consider performance implications of changes
- Use async/await for I/O operations
- Implement proper connection pooling
- Add performance tests for critical paths

## 🤝 Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the project's code of conduct

### Communication

- Use clear, professional language
- Be patient with newcomers
- Ask questions when needed
- Share knowledge and experiences

## 📞 Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: team@meshmind.ai for private matters

## 🙏 Recognition

Contributors will be recognized in:

- GitHub contributors list
- Release notes
- Project documentation
- Community acknowledgments

Thank you for contributing to MeshMind! 🚀
