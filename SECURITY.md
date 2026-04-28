# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please follow these steps:

1. **Do not open a public issue.** Security vulnerabilities should be reported privately.
2. Email the maintainers at the contact listed in the repository.
3. Include a detailed description of the vulnerability, steps to reproduce, and any potential impact.
4. Allow reasonable time for the maintainers to address the issue before any public disclosure.

## Security Best Practices

- All changes are reviewed via pull request.
- CI/CD pipelines run automated security checks.
- Dependencies are kept up to date and scanned for known vulnerabilities.

## Vulnerability Triage SLA

Dependency vulnerabilities found by `pip-audit` block CI until they are remediated
or explicitly accepted with a documented allowlist entry. Confirmed vulnerabilities
are triaged by severity:

| Severity | Triage target | Remediation target |
| -------- | ------------- | ------------------ |
| Critical | 1 business day | 7 calendar days |
| High     | 2 business days | 30 calendar days |
| Medium   | 5 business days | 60 calendar days |
| Low      | 10 business days | Next regular maintenance cycle |

If a vulnerable dependency cannot be upgraded safely within the target window,
maintainers must document the compensating control, planned follow-up, and review
date before adding or extending any allowlist exception.

## Disclosure Policy

Once a vulnerability is confirmed and a fix is released, we will publicly disclose the issue in our [CHANGELOG](CHANGELOG.md) and credit the reporter (if desired).
