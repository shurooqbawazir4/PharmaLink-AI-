# PharmaLink AI — Cross-cutting integration tests

Backend-only integration/unit tests live in `backend/tests/` (see
`docs/architecture.md`). This top-level directory is reserved for tests
that span multiple services — e.g. frontend-against-live-backend E2E, or
full docker-compose smoke tests — once there's more than one service to
cross. Empty until Milestone D/E.
