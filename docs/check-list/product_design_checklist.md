# Schema-Driven Product Design – Daily Checklist

Use this when planning or updating **any product/feature**.
Goal: be implementation-ready, proto-first, and consistent.

---

## 1. Role & Goal

**You are:** VP / Principal Product Designer.

**Your job today:**
Produce an implementation-grade spec where **protobuf is the source of truth** and everything else (API, DB, events, frontend, tests) is derivable from it.

---

## 2. Requirements

### 2.1 Functional Requirements

* [ ] List **FR-1, FR-2, …**

  * Each FR is **one behavior**, externally observable, testable.
  * No vague words (“fast”, “robust”) without numbers.

### 2.2 Non-Functional Requirements

* [ ] List **NFR-1, NFR-2, …** with tags, e.g. `[Performance]`, `[Security]`, `[Reliability]`.

  * [ ] Performance targets (latency, throughput).
  * [ ] Reliability / uptime.
  * [ ] Security / auth model.
  * [ ] Observability (logs/metrics/traces).
  * [ ] Data retention / privacy.

### 2.3 Acceptance Criteria

* [ ] For key FRs, write **GIVEN / WHEN / THEN** scenarios.

  * [ ] At least **one AC per critical FR**.

---

## 3. Domain Model

* [ ] List **Entities** with purpose + key fields.
* [ ] Define **relationships** (has-many, belongs-to, etc.).
* [ ] Identify **Value Objects** (e.g. TimeRange, Money).
* [ ] For entities with lifecycle:

  * [ ] Define **states** and **allowed transitions**.
  * [ ] Note invariants (what must never happen).

---

## 4. Protobuf Schema (Source of Truth)

* [ ] Choose package name (e.g. `product.feature.v1`).
* [ ] Define **Messages** for main entities.

  * [ ] Fields use `snake_case` and clear types.
  * [ ] Time fields use explicit units (e.g. `*_ms`).
* [ ] Define **Request/Response messages** for each RPC.
* [ ] Define **Services** with RPCs.
* [ ] For each field:

  * [ ] No renumbering or reusing tags.
  * [ ] If planning a removal, note **`reserved`** tags/fields (future proof).

*(No long examples here; proto content lives in code repo.)*

---

## 5. API / HTTP Design

For each external operation:

* [ ] Map RPC → HTTP:

  * [ ] Method (GET/POST/PUT/PATCH/DELETE).
  * [ ] Path (incl. path params).
  * [ ] Which proto message is the **request body**?
  * [ ] Which proto message is the **response body**?
* [ ] Auth & permissions:

  * [ ] Who can call this? Which scope/role?
* [ ] Status codes & errors (high level):

  * [ ] Success: `200` / `201` / `202` / `204` as appropriate.
  * [ ] Common 4xx: `400 INVALID_ARGUMENT`, `401 UNAUTHENTICATED`,
    `403 PERMISSION_DENIED`, `404 NOT_FOUND`, `409 CONFLICT/ALREADY_EXISTS`,
    `429 RESOURCE_EXHAUSTED`.
  * [ ] Common 5xx: `500 INTERNAL`, `503 UNAVAILABLE`, `504 DEADLINE_EXCEEDED`.
* [ ] Note **idempotency** behavior where relevant.

---

## 6. Storage & Indexing

For each main entity:

* [ ] Define **table/collection** name.
* [ ] Map **proto fields → columns** (types, nullability).
* [ ] Primary key and any **unique constraints**.
* [ ] **Indexes** to support key queries.
* [ ] Foreign keys / relationships.

---

## 7. Dataflow & Events (If Applicable)

* [ ] Do we emit or consume async **events**? If no, skip.
* [ ] For each stream:

  * [ ] Name of the stream/topic.
  * [ ] Event message type (backed by proto).
  * [ ] Producers.
  * [ ] Consumers.
  * [ ] Delivery semantics (at-least-once, etc.).
  * [ ] Ordering guarantees (per key / best effort).

---

## 8. Frontend & UX Contract

For each relevant UI view:

* [ ] Name the **view/page**.
* [ ] Which endpoint(s) it calls.
* [ ] Which **fields** from which proto messages it uses.
* [ ] List core UI states:

  * [ ] Loading / success / empty / error.
* [ ] Note any **client-side types** (TS interfaces) that mirror the proto JSON.

---

## 9. Observability & SLOs

* [ ] Logs: which actions must log, and which fields (IDs, project/org, status, latency, error code).
* [ ] Metrics: which counters/gauges/histograms you need (per operation).
* [ ] Traces: where traces start; what context is propagated.
* [ ] SLOs: target latency/error rates and what will be monitored.

---

## 10. Testing, Rollout & Risks

* [ ] **Unit tests:** key success & failure paths for each operation.
* [ ] **Integration tests:** main end-to-end flows.
* [ ] **Contract tests:** shape and types match proto; enums & fields stable.
* [ ] **Rollout plan:** flags, staged rollout, rollback strategy.
* [ ] **Migrations:** DB schema changes + verification steps.
* [ ] **Risks & open questions:** listed with owners & deadlines.

---

## 11. Final Self-Check (Daily)

Before you say “design ready”:

```text
[ ] Requirements (FR/NFR + AC) are concrete and testable.
[ ] Domain model is clear (entities, relationships, states).
[ ] Proto schema covers all external interactions; no ad-hoc JSON.
[ ] HTTP APIs, status codes, and auth are defined per operation.
[ ] Storage and indexes derive cleanly from proto.
[ ] Events/dataflow are explicit (or explicitly not used).
[ ] Frontend knows exactly which fields it consumes.
[ ] Observability and SLOs are specified for key paths.
[ ] Tests, rollout, and migrations are at least outlined.
[ ] No critical TODOs remain; uncertainties are captured as “open questions”.
```
