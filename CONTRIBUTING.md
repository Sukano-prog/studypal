# Contributing to StudyPal

We love your input! We want to make contributing to StudyPal as easy and transparent as possible.

## Development Process

1. Fork the repo and create your branch from `main`
2. If you have added code that should be tested, add tests
3. If you have changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code is properly formatted
6. Issue that pull request!

## Development Setup

```bash
git clone https://github.com/your-username/studypal.git
cd studypal
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Code Style

- Use [Black](https://github.com/psf/black) for code formatting
- Use [isort](https://github.com/PyCQA/isort) for import sorting
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)

## Testing

```bash
pytest tests/
```

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the CHANGELOG.md with your changes
3. The PR will be merged once you have the sign-off of at least one maintainer

## Any contributions you make will be under the MIT Software License

When you submit code changes, your submissions are understood to be under the same [MIT License](LICENSE) that covers the project.
