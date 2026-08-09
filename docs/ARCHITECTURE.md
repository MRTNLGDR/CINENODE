# Architecture

CineNode is divided into replaceable modules: configuration, SQLite persistence, store, typed node registry, DAG compiler, durable job service, cache, event bus, engine adapters, plugin SDK, backup/restore, security middleware, FastAPI transport and a dependency-free web canvas. No module imports PERZON. Engine registries are instance-scoped so one application cannot contaminate another.

The default deployment is a single-user local process bound to loopback. The same API can run in authenticated server mode. Model runtimes stay out-of-process and are reached through adapters, allowing the orchestration core to be reused by desktop, web, game, media and enterprise products.
