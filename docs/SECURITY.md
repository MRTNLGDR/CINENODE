# Security model

Local mode accepts loopback clients only and requires no browser token. Server mode requires an explicit long token. Public configuration is redacted. Engine URLs are loopback-only by default, uploads are streamed and bounded, file paths are normalized, ZIP restore rejects traversal, backups verify SHA-256, and model weights/secrets/runtime databases are excluded from Git.

A reverse proxy must provide TLS, rate limits and identity integration for internet exposure. Biometric or regulated data requires a separate threat model and compliance review.
