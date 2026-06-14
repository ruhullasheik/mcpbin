# Security Policy

## Supported versions

mcpbin is pre-1.0; only the **latest release** receives fixes. Please reproduce issues
against the most recent `v0.x` tag (or `main`) before reporting.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately via GitHub's **"Report a vulnerability"** button on the repository's
**Security** tab (Private Vulnerability Reporting). If that is unavailable, contact the
maintainer **[@ruhullasheik](https://github.com/ruhullasheik)** directly.

Please include: a description, reproduction steps, affected version/commit, and impact. We
aim to acknowledge reports within a few days and will coordinate a fix and disclosure timeline
with you.

## Scope notes

mcpbin is a **diagnostic test server** that intentionally returns error codes, simulated
errors, and edge-case responses, and (in the `full` profile) issues `sampling/createMessage`
requests back to the connected client. The public demo instance is unauthenticated by design
and is not intended to hold or process sensitive data. Reports should focus on issues beyond
this documented, intentional behavior (e.g. unexpected code execution, data exposure, or
denial-of-service in the server itself).
