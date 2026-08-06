# Contributing to Maparr

Thank you for considering contributing to Maparr! This document outlines the process for helping improve this project.

## Getting Started

1. Fork the repository on git.fyrek.dev
2. Clone your fork locally:
   ```bash
   git clone https://git.fyrek.dev/<your-username>/maparr.git
   cd maparr
   ```
3. Set up the development environment:
   ```bash
   make install
   ```
4. Create a branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Backend (Python)

- The backend is a FastAPI application located in `./backend/`
- Run tests with: `make test`
- Lint with: `make lint`
- Type checking is done via `ruff` and `mypy` (configured in pyproject.toml)
- Database migrations are handled automatically on startup (SQLite by default)

### Frontend (React + TypeScript)

- The frontend is located in `./frontend/`
- Uses Vite for fast development builds
- Run `make frontend-dev` for hot-reloading development server
- Type-check with: `make type-check`
- Lint with: `make lint` (uses ESLint + Prettier)

### Database

- Default is SQLite file at `data/maparr.db`
- For production, consider using PostgreSQL by changing `MAPARR_DATABASE_URL`
- The database schema is managed via SQLAlchemy models in `backend/maparr/models.py`

## Making Changes

Please ensure your changes follow these guidelines:

1. **Code Style**
   - Backend: Follow PEP 8, enforced by `ruff`
   - Frontend: Follow TypeScript ESLint rules, formatted with Prettier
   - Both: Keep line lengths reasonable (<= 100 chars)

2. **Commits**
   - Write clear, concise commit messages
   - Reference issues if applicable: `fix: resolve login issue (#123)`
   - Keep commits atomic and focused

3. **Testing**
   - Add unit tests for new backend functionality in `backend/tests/`
   - Add integration tests where appropriate
   - Frontend tests are encouraged but not required initially

4. **Documentation**
   - Update docstrings for new Python functions/classes
   - Add JSDoc comments for complex TypeScript logic
   - If adding new API endpoints, update the OpenAPI schema implicitly via FastAPI

## Submitting Changes

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
2. Open a Pull Request against the `main` branch of the main repository.
3. Fill in the PR template with a clear description of what and why.
4. Ensure all CI checks pass before requesting review.
5. Address any feedback from maintainers.

## Reporting Issues

Please use the issue tracker on git.fyrek.dev to report bugs or request features. Include:
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Logs or screenshots if applicable
- Your environment (OS, Python version, etc.)

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

Thank you again for your contribution!