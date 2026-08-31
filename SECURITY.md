# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 3.0.x   | :white_check_mark: |
| 2.3.x   | :white_check_mark: |
| 2.2.x   | :x:                |
| < 2.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in FraudShield, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

### How to Report

1. Email: [muditbhargava666@gmail.com](mailto:muditbhargava666@gmail.com)
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours of receipt
- **Assessment**: Initial triage within 5 business days
- **Resolution**: Target patch release within 30 days for confirmed vulnerabilities
- **Disclosure**: Coordinated disclosure after fix is available

### Scope

The following are in scope:

- SQL injection in connection strings or queries
- Credential exposure in logs, errors, or configuration
- Buffer overflows or memory safety issues in C++ modules
- Dependency vulnerabilities with known CVEs
- Authentication/authorization bypass in the inference API
- Data leakage through feature engineering

The following are out of scope:

- Vulnerabilities in third-party services (Kafka, Neo4j, PostgreSQL)
- Issues requiring physical access to the host machine
- Social engineering attacks

## Security Measures

FraudShield implements the following security controls:

- **SQL injection prevention**: All queries use parameterized `text()` bindings via SQLAlchemy
- **Credential management**: Environment variables only, never hardcoded
- **Dependency pinning**: Vulnerable transitive dependencies pinned via `[tool.uv] override-dependencies`
- **Type safety**: mypy static type checking on all source files
- **Linting**: Ruff for code quality and security-relevant checks
- **C++ safety**: Bounds checking, NULL pointer validation, and buffer overflow prevention in all C++ modules

## Dependency Updates

Vulnerable dependencies are tracked and updated regularly. To check for known vulnerabilities:

```bash
# Audit every runtime extra exported from the uv lockfile
uv export --all-extras --no-dev --no-emit-project --no-hashes --locked \
  --output-file /tmp/fraudshield-audit-requirements.txt
uvx pip-audit --no-deps --disable-pip -r /tmp/fraudshield-audit-requirements.txt --strict
```

## Responsible Disclosure

We appreciate responsible disclosure. Reporters of valid security issues will be credited in the changelog (unless they prefer to remain anonymous).

---
