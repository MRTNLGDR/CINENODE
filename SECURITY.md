# Security

CineNode binds to loopback by default. LAN/server mode requires an explicit authentication token. Secrets are never returned by public settings endpoints. Engine URLs are restricted to loopback by default; private-network destinations require explicit configuration. Uploads and downloads are streamed with size limits, archives are checked for path traversal, and model downloads may require an expected SHA-256.

Report vulnerabilities privately to the repository owner. Do not include tokens, biometric data, model weights or user databases in issues.
