# Second Brain Chrome Extension - Frontend

Chrome Extension for capturing ChatGPT and Claude conversations to Second Brain.

## Setup

```bash
npm install
```

## Development

```bash
# Build extension
npm run build

# Development mode with watch
npm run dev

# Type checking
npm run typecheck

# Linting
npm run lint
npm run lint:fix

# Formatting
npm run format
npm run format:check

# Testing
npm test
npm run test:watch
npm run test:coverage
npm run test:e2e
```

## Project Structure

```
frontend/
├── src/
│   ├── background/      # Service worker and background scripts
│   ├── content/         # Content scripts and parsers
│   ├── popup/           # Popup UI
│   ├── shared/          # Shared utilities and types
│   └── styles/          # CSS files
├── tests/               # Test files
├── dist/                # Build output (generated)
└── manifest.json        # Chrome Extension manifest (V3)
```

## Code Quality

- **TypeScript**: Strict mode enabled
- **ESLint**: TypeScript + recommended rules
- **Prettier**: Code formatting
- **Jest**: Unit and E2E testing
- **100% Coverage**: Required for all core modules

## Pre-commit Hooks

All commits are validated with:

- Type checking
- Linting
- Formatting
- Tests
- Coverage checks

## Build Output

The `dist/` directory contains the built extension ready for Chrome Web Store submission.
