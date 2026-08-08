# Local API

Base URL: `http://127.0.0.1:8787`. All API and media endpoints are local-only by default.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Runtime readiness and active job. |
| GET | `/api/bootstrap` | App metadata, preferences and node catalog. |
| GET/POST | `/api/projects` | List/create projects. |
| GET/PUT/DELETE | `/api/projects/{id}` | Read/update/delete. |
| POST | `/api/projects/{id}/export` | Export project package. |
| POST | `/api/workflows/validate` | Validate graph, ports and cycles. |
| GET | `/api/nodes/catalog` | Available node definitions. |
| GET/POST | `/api/jobs` | List/queue executions. |
| GET | `/api/jobs/{id}` | Job state/result/error. |
| POST | `/api/jobs/{id}/cancel` | Request cancellation. |
| POST | `/api/jobs/{id}/retry` | Clone graph into a new job. |
| GET | `/api/assets` | Gallery metadata. |
| POST | `/api/assets/upload` | Streamed, limited, sanitized upload. |
| GET | `/media/{asset_id}` | Serve a registered local asset. |
| GET/PATCH | `/api/settings` | Read/update permitted settings. |
| GET | `/api/engines/status` | Real binary/server checks. |
| GET | `/api/model-profiles` | Profiles plus missing file list. |
| GET | `/api/governance/snapshot` | Single source of truth. |
| PATCH | `/api/governance/tasks/{id}` | Update status/evidence. |
| GET | `/api/events` | SSE stream. |
| GET/POST | `/api/backups` | List/create backups. |
| POST | `/api/backups/restore` | Validated restore. |

Errors use an explicit code/message. Missing engines and models are failures, never generated placeholders.
