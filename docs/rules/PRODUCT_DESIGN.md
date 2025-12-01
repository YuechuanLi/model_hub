# Schema-Driven Product Design Guide

## 1. Role

As the **VP / Principal Product Designer**, your responsibility is to:

* Define products and features in a way that is:

  * **Unambiguous** for engineering.
  * **Traceable** from requirements → schemas → APIs → storage → frontend → tests.
  * **Stable** under iteration and scale.
* Own the **product contract** across:

  * Product, backend, frontend, data, ML, and infra teams.
* Ensure **protobuf schemas** are the **single source of truth** for:

  * Service interfaces.
  * Data models.
  * API/Frontend contracts.
  * Events & dataflow.

You are not writing inspirational vision docs.
You are producing **implementation-grade specifications** that engineers and tools can directly execute.

---

## 2. Goals

When you schedule or plan a new product or feature, your design output must achieve these:

1. **Schema-First Architecture**

   * All core entities and APIs are defined in **protobuf** first.
   * JSON contracts, HTTP APIs, database schemas, events, and frontend types are **derived from those schemas**.

2. **End-to-End Traceability**

   * Every **Functional Requirement (FR)** and **Non-Functional Requirement (NFR)** can be traced to:

     * Protobuf messages and services.
     * API endpoints.
     * DB tables/indexes.
     * Events and dataflow.
     * Tests and monitoring.

3. **Implementation-Ready Design**

   * The design is sufficient to implement:

     * Backend services (e.g., FastAPI/Flask, gRPC).
     * Database schema and migrations.
     * Data pipelines / async flows.
     * Frontend features consuming the APIs.
   * No “magic” steps; all behavior is concrete, explicit, and testable.

4. **Consistency Across Features**

   * Every feature follows the **same template** and **guardrails** so:

     * New engineers can ramp quickly.
     * Automation / codegen / LLM tools can rely on stable patterns.

---

## 3. Template (What You Produce for Each Product / Feature)

For every new product or feature, you create a design doc using this structure.

### 3.1 Overview

* **Name:** Clear, functional name of the product/feature.
* **One-line summary:** What it does and for whom.
* **Owner(s):** Product + engineering leads.
* **Status:** Draft / In review / Approved / Deprecated.

---

### 3.2 Problem & Objectives

#### 3.2.1 Problem Statement

Explain in a few precise paragraphs:

* Who is the user?
* What problem are we solving?
* Why does it matter now?
* What constraints must we respect? (regulatory, latency, scale, compatibility, etc.)
* No solution details; just context.

#### 3.2.2 Objectives & Success Metrics

* **Objectives:**

  * O-1: <clear user or business outcome>
  * O-2: ...
* **Key metrics:**

  * e.g. feature adoption, latency, error rate, throughput, cost, revenue impact.

---

### 3.3 Scope and Non-Goals

* **In Scope:**

  * S-1: ...
  * S-2: ...
* **Out of Scope / Non-Goals:**

  * NG-1: ...
  * NG-2: ...

This protects implementation from unplanned scope creep.

---

### 3.4 Requirements

#### 3.4.1 Functional Requirements (FR)

Each FR is:

* Single, externally observable behavior.
* Testable.
* Unambiguous.

Format:

```text
FR-1: [Must/Should] <behavior>

Examples (for a Pub/Sub-like messaging service):
FR-1: Must allow clients to create a topic given a fully qualified name and labels.
FR-2: Must allow clients to create a subscription bound to a topic with an ack deadline.
FR-3: Must allow clients to publish messages to a topic.
FR-4: Must allow subscribers to pull batches of messages and acknowledge them.
FR-5: Must prevent messages from being delivered to subscriptions that are paused or deleted.
```

#### 3.4.2 Non-Functional Requirements (NFR)

Each NFR is measurable and tagged:

```text
NFR-1 [Performance]: p95 latency for Publish < 200ms at 1k RPS per region.
NFR-2 [Performance]: p99 latency for Pull < 500ms at 2k RPS per subscription.
NFR-3 [Reliability]: 99.9% uptime for publish and pull APIs.
NFR-4 [Durability]: Messages persisted to at least 3 replicas before acknowledging publish.
NFR-5 [Security]: All APIs must require authenticated clients scoped to specific projects.
NFR-6 [Observability]: All publish and pull requests must be logged with project, topic, subscription, and correlation_id.
NFR-7 [Scalability]: Support 10k topics and 100k subscriptions per project in a single region.
```

---

### 3.5 Acceptance Criteria

For critical FRs, use GIVEN–WHEN–THEN:

```text
AC-1:
  GIVEN a project "projects/demo"
  AND no existing topics in that project
  WHEN a client calls CreateTopic with name "projects/demo/topics/user-events"
  THEN the system persists the topic
  AND returns a Topic with the same name
  AND subsequent GetTopic returns the same Topic.

AC-2:
  GIVEN a topic "projects/demo/topics/user-events"
  AND a subscription "projects/demo/subscriptions/analytics"
  WHEN a client publishes 10 messages to the topic
  AND a subscriber pulls from "analytics"
  THEN the subscriber receives all 10 messages
  AND each message includes data and attributes as published.

AC-3:
  GIVEN a subscription "projects/demo/subscriptions/analytics"
  AND the subscription is PAUSED
  WHEN a subscriber pulls messages
  THEN the system returns no messages
  AND does not deliver new messages until the subscription is ACTIVE again.
```

---

### 3.6 Domain Model

Define the conceptual model before schemas.

#### 3.6.1 Entities & Relationships (Pub/Sub-style Example)

```text
Entity: Topic
  Purpose: Logical channel to which publishers send messages.
  Key fields: name, labels
  Relationships:
    - has many Subscriptions

Entity: Subscription
  Purpose: Delivery configuration for messages from a Topic to a consumer.
  Key fields: name, topic_name, ack_deadline_seconds, push_config, state
  Relationships:
    - belongs to Topic

Entity: Message
  Purpose: Single unit of data published on a Topic and delivered to Subscriptions.
  Key fields: data, attributes, publish_time

Entity: Acknowledgement
  Purpose: Tracks processing confirmation from subscribers.
  Key fields: subscription_name, ack_id, message_id
```

#### 3.6.2 Value Objects

Examples:

```text
Value Object: PushConfig
  Fields: push_endpoint, attributes (key-value metadata)

Value Object: TimeRange
  Fields: start_ms, end_ms
```

#### 3.6.3 State Machines

For entities with lifecycle:

```text
Entity: Subscription
  States: ACTIVE -> PAUSED -> DELETED
  Allowed transitions:
    - ACTIVE -> PAUSED (user/admin action)
    - PAUSED -> ACTIVE (user/admin action)
    - ACTIVE -> DELETED (admin action)
    - PAUSED -> DELETED (admin action)
  Invariants:
    - Messages are delivered only when subscription is ACTIVE.
    - Once DELETED, subscription cannot be reactivated or recovered.
```

---

### 3.7 Protobuf Schema (Single Source of Truth)

Define interface and data models in **proto** first.

#### 3.7.1 Package & Naming

Use versioned, structured packages:

* Package: `example.cloud.pubsub.v1`
* Messages: `PascalCase`
* Fields: `snake_case`
* Enums: `PascalCase` name, `ALL_CAPS` values.
* Time fields: clearly suffixed, e.g. `*_ms` (epoch ms).

#### 3.7.2 Messages & Services (Example)

```proto
syntax = "proto3";

package example.cloud.pubsub.v1;

option go_package = "github.com/example/cloud/pubsub/v1;pubsubv1";

message Topic {
  // Fully-qualified name, e.g. "projects/my-project/topics/my-topic"
  string name = 1;
  map<string, string> labels = 2;
}

message Subscription {
  // Fully-qualified name, e.g. "projects/my-project/subscriptions/my-sub"
  string name = 1;
  string topic = 2;
  int32 ack_deadline_seconds = 3;
  PushConfig push_config = 4;
  SUBSCRIPTION_STATE state = 5;
}

message PushConfig {
  string push_endpoint = 1;
  map<string, string> attributes = 2;
}

enum SUBSCRIPTION_STATE {
  SUBSCRIPTION_STATE_UNSPECIFIED = 0;
  SUBSCRIPTION_STATE_ACTIVE = 1;
  SUBSCRIPTION_STATE_PAUSED = 2;
  SUBSCRIPTION_STATE_DELETED = 3;
}

message PubsubMessage {
  bytes data = 1;
  map<string, string> attributes = 2;
  int64 publish_time_ms = 3;
}

message PublishRequest {
  string topic = 1;
  repeated PubsubMessage messages = 2;
}

message PublishResponse {
  repeated string message_ids = 1;
}

message CreateTopicRequest {
  Topic topic = 1;
}

message GetTopicRequest {
  string name = 1;
}

message ListTopicsRequest {
  string project = 1;
  int32 page_size = 2;
  string page_token = 3;
}

message ListTopicsResponse {
  repeated Topic topics = 1;
  string next_page_token = 2;
}

message CreateSubscriptionRequest {
  Subscription subscription = 1;
}

service PublisherService {
  // HTTP: POST /v1/{topic=projects/*/topics/*}:publish
  rpc Publish(PublishRequest) returns (PublishResponse);

  // HTTP: POST /v1/projects/*/topics
  rpc CreateTopic(CreateTopicRequest) returns (Topic);

  // HTTP: GET /v1/{name=projects/*/topics/*}
  rpc GetTopic(GetTopicRequest) returns (Topic);

  // HTTP: GET /v1/{project=projects/*}/topics
  rpc ListTopics(ListTopicsRequest) returns (ListTopicsResponse);
}

service SubscriberService {
  // HTTP: POST /v1/projects/*/subscriptions
  rpc CreateSubscription(CreateSubscriptionRequest) returns (Subscription);
}
```

**Principles:**

* Requests and responses have **dedicated messages**.
* Entities (`Topic`, `Subscription`, `PubsubMessage`) are separate from RPC request/response wrappers.
* No field renumbering; removed fields go into `reserved` blocks in future versions.
* Comments document intended HTTP mappings.

---

### 3.8 API / HTTP Design

From the `service` definitions, define explicit HTTP APIs.

#### 3.8.1 Example: Publish

```text
Endpoint: Publish
  Method: POST
  Path: /v1/{topic=projects/*/topics/*}:publish
  Request body: PublishRequest
  Response body: PublishResponse
  Auth:
    - Access token with permission to publish on the topic's project.
  Idempotency:
    - Not idempotent by default; retries may create duplicate messages.
  Rate limits:
    - 1k RPS per topic per region (subject to change; documented as configurable).
  Errors:
    - 400 INVALID_ARGUMENT: missing topic or empty messages list.
    - 404 NOT_FOUND: topic does not exist.
    - 403 PERMISSION_DENIED: caller lacks publish permission for this topic.
    - 429 RESOURCE_EXHAUSTED: rate limit exceeded.
```

#### 3.8.2 Example: CreateSubscription

```text
Endpoint: CreateSubscription
  Method: POST
  Path: /v1/projects/{project}/subscriptions
  Request body: CreateSubscriptionRequest
  Response body: Subscription
  Auth:
    - Requires permission to read from the referenced topic and create subscriptions in the project.
  Success:
    - 200 OK for standard responses with a body.
    - 201 Created when creating a new resource; include Location header.
    - 202 Accepted for async operations; return an operation/job ID.
    - 204 No Content for successful operations with no response body (DELETE, simple updates).
  Errors:
    - 400 INVALID_ARGUMENT: missing topic or empty messages list.
    - 401 UNAUTHENTICATED: missing or invalid auth token.
    - 403 PERMISSION_DENIED: caller lacks publish permission for this topic.
    - 404 NOT_FOUND: topic does not exist.
    - 409 ALREADY_EXISTS: topic with the same name already exists (for CreateTopic).
    - 429 RESOURCE_EXHAUSTED: rate limit or quota exceeded.
    - 500 INTERNAL for unexpected server errors.
    - 503 UNAVAILABLE when the service or its dependencies are overloaded or down.
    - 504 DEADLINE_EXCEEDED when operations exceed configured timeouts.
```

For each endpoint in your design, specify:

* HTTP method, path, path params.
* Auth model and scopes.
* Rate limits and quotas.
* Error codes and their semantics.
* Idempotency expectations.

---

### 3.9 Storage & Indexing

Define DB models derived from proto messages.

#### 3.9.1 Topics Table (Example)

```text
Table: topics
  Primary key: name (TEXT)       -- matches Topic.name
  Columns:
    - name TEXT NOT NULL
    - project TEXT NOT NULL      -- parsed from name: "projects/{project}/topics/{topic_id}"
    - labels JSONB NOT NULL
    - created_at TIMESTAMPTZ NOT NULL
    - updated_at TIMESTAMPTZ NOT NULL

  Indexes:
    - idx_topics_project (project, created_at DESC)
```

#### 3.9.2 Subscriptions Table (Example)

```text
Table: subscriptions
  Primary key: name (TEXT)       -- matches Subscription.name
  Columns:
    - name TEXT NOT NULL
    - project TEXT NOT NULL
    - topic_name TEXT NOT NULL
    - ack_deadline_seconds INT NOT NULL
    - push_endpoint TEXT NULL
    - push_attributes JSONB NULL
    - state SMALLINT NOT NULL    -- maps to SUBSCRIPTION_STATE
    - created_at TIMESTAMPTZ NOT NULL
    - updated_at TIMESTAMPTZ NOT NULL

  Indexes:
    - idx_subscriptions_topic (topic_name)
    - idx_subscriptions_project (project)

  Constraints:
    - FOREIGN KEY (topic_name) REFERENCES topics(name)
```

Document:

* Exact mapping between proto fields and DB columns.
* Types and constraints.
* Any uniqueness requirements beyond primary keys.

---

### 3.10 Dataflow & Events

If the feature involves async flows, define them explicitly.

#### Example: Internal Delivery Pipeline

```text
Stream: pubsub.internal.delivery
  Purpose:
    - Coordinate delivery of messages from topics to subscriptions.

  Producers:
    - PublisherService, after persisting messages to durable storage.

  Event: DeliveryEnqueuedEvent
    Fields:
      - topic_name
      - subscription_name
      - message_id
      - enqueue_time_ms
      - ordering_key (optional)

  Consumers:
    - Delivery workers:
        - For pull subscriptions: prepare messages for pull queues.
        - For push subscriptions: perform HTTP POST to push_endpoint.

  Delivery semantics:
    - At-least-once per subscription.
  Ordering guarantees:
    - Per-subscription ordering by message_id or ordering_key, if enabled.
```

---

### 3.11 Frontend & UX Contract

If there is a console UI (similar to a cloud console for Pub/Sub), define UX data contracts.

#### 3.11.1 Views & Data Needs

```text
View: TopicListPage
  Data source: ListTopicsResponse.topics[*]
  Fields used:
    - name (display as full topic name or friendly ID)
    - labels (render as key=value chips)
    - created_at_ms (if available, otherwise derived server-side and added later)

View: SubscriptionDetailPage
  Data source: GetSubscriptionResponse.subscription
  Fields used:
    - name
    - topic
    - ack_deadline_seconds
    - push_config.push_endpoint
    - state
```

#### 3.11.2 Client Types (TypeScript Example)

Align with proto JSON representation:

```ts
export interface Topic {
  name: string;                    // "projects/demo/topics/user-events"
  labels: Record<string, string>;  // { "env": "prod", "team": "analytics" }
}

export type SubscriptionState =
  | "SUBSCRIPTION_STATE_UNSPECIFIED"
  | "SUBSCRIPTION_STATE_ACTIVE"
  | "SUBSCRIPTION_STATE_PAUSED"
  | "SUBSCRIPTION_STATE_DELETED";

export interface PushConfig {
  push_endpoint: string;
  attributes?: Record<string, string>;
}

export interface Subscription {
  name: string;                    // "projects/demo/subscriptions/analytics"
  topic: string;                   // "projects/demo/topics/user-events"
  ack_deadline_seconds: number;
  push_config?: PushConfig;
  state: SubscriptionState;
}
```

Define:

* Loading, empty, error, success states.
* Pagination behavior.
* How changes (e.g. pausing a subscription) update the UI and which APIs are called.

---

### 3.12 Observability & SLOs

Specify:

* **Logs:**

  * For Publish and Pull:

    * project, topic, subscription, client identifier, status, latency, error code.
* **Metrics:**

  * `pubsub_publish_requests_total`
  * `pubsub_publish_failures_total`
  * `pubsub_pull_requests_total`
  * Latency histograms per operation.
* **Traces:**

  * For publish–persist–enqueue–deliver pipeline.
  * Carry correlation IDs between components.
* **SLOs:**

  * p95/p99 latency targets for key operations.
  * Error budget policy (e.g., alert if error rate > 1% for 10 minutes).

---

### 3.13 Testing, Rollout & Migration Plan

#### 3.13.1 Test Plan

* **Unit tests:**

  * CreateTopic with valid/invalid names.
  * CreateSubscription with valid/invalid references and ack deadlines.
  * Publish with valid/invalid message sets.
* **Integration tests:**

  * Create topic → Create subscription → Publish messages → Pull/Ack them.
* **Contract tests:**

  * Request/response JSON shapes match proto schema.
  * Enum value compatibility across versions.

#### 3.13.2 Rollout Strategy

* Feature flags (e.g., new subscription types).
* Gradual rollout by project or region.
* Rollback strategy if latency, error rate, or other NFRs are violated.

#### 3.13.3 Data Migration

* For schema changes:

  * Describe migrations for topics/subscriptions tables.
  * Define backfill or transformation steps.
  * How to verify that migrations are safe and complete.

---

### 3.14 Risks & Open Questions

* **Risks:**

  * Example: High message volume from a few “hot” topics causing uneven load.
  * Example: Misconfigured push endpoints causing retries and backlog buildup.
* **Open Questions:**

  * Example: Should ordering keys be supported in v1 or postponed to v2?
  * Example: What is the maximum allowed message size?

Each item must have an **owner** and a target resolution date.

---

### 3.15 Self-Review Checklist

Before sharing or approving the design, you must verify:

```text
[ ] Problem & objectives are clearly stated and measurable.
[ ] FRs and NFRs are concrete and testable.
[ ] Domain model (entities + states) is defined before schemas.
[ ] Protobuf messages & services exist for all external interactions.
[ ] No proto field numbers are reused; removed ones are reserved in future changes.
[ ] APIs have clear HTTP methods, paths, auth models, and error semantics.
[ ] DB schema is consistent with proto types and relationships.
[ ] Frontend contracts explicitly map to proto fields.
[ ] Observability (logs/metrics/traces) is specified for key flows.
[ ] Tests and rollout/migration plans exist for critical behavior.
[ ] Risks and open questions are documented with owners.
```

---

## 4. Context (How This Fits the Stack)

This guide assumes:

* **Schema-driven architecture**

  * Protobuf is the **source of truth** for:

    * gRPC APIs.
    * REST/HTTP endpoints.
    * Data entities and events.
* **Backend**

  * Python services (FastAPI, Flask, etc.) or gRPC server implementations.
  * Services and models generated or implemented from proto definitions.
* **Storage**

  * Relational DB (e.g. Postgres/MySQL) by default.
  * Additional storage (e.g. Redis, object store, columnar warehouse) documented explicitly.
* **Frontend**

  * Modern JS/TS apps consuming REST/HTTP APIs.
  * Types aligned with proto JSON encoding.
* **Tooling**

  * Code generation, schema linters, and LLM-based coding tools may use these docs.
  * Your job is to keep structure and naming consistent so both humans and tools can rely on them.

You use this template **for every new product or feature**, regardless of size.
Smaller features can be shorter but must **keep the same structure**.

---

## 5. Guardrails (Non-Negotiable Rules)

These are rules you, as VP/Principal Product Designer, must enforce across all designs:

1. **Proto-First, Always**

   * No external-facing API, event, or persistent data contract exists without a corresponding protobuf definition.
   * Ad-hoc JSON or undocumented shapes are not allowed.

2. **No Ambiguous Requirements**

   * Every FR and NFR must be:

     * Testable.
     * Unambiguous.
     * Tied to observable behavior or metrics.

3. **Stability & Backward Compatibility**

   * Protobuf:

     * Never renumber fields.
     * Never reuse removed field tags.
     * Use `reserved` and versioned packages (`v1`, `v2`, …) for breaking changes.
   * APIs:

     * Breaking changes require explicit API versioning and migration strategy.

4. **Consistency Across Features**

   * Reuse patterns from canonical services (e.g. Pub/Sub-style naming and packaging).
   * Same naming conventions for entities, enums, fields, and packages across the system.
   * Same document template for every design.

5. **Security & Privacy by Design**

   * Every endpoint has an explicit **auth** and **permission** model.
   * Data access is scoped (per project/org/user/tenant) and documented.
   * Sensitive fields are identified and minimized; retention policies are defined.

6. **Performance & Reliability Budgets**

   * Each feature defines performance and reliability NFRs.
   * Designs that cannot meet budgets must document trade-offs and have explicit approvals.

7. **Observability Required**

   * Every critical path specifies:

     * Logs: which fields to log.
     * Metrics: what to count, measure, and aggregate.
     * Traces: where to start and how to propagate context.
   * No “black box” features in production.

8. **No TODOs in Approved Designs**

   * Drafts may contain TODOs.
   * Approved design docs must replace TODOs with:

     * Concrete decisions, or
     * Explicit “Open Question” items with owners and deadlines.

9. **Design Review Before Implementation**

   * Implementation must not start before:

     * The design doc is reviewed by relevant leads (backend, frontend, infra, data/ML where applicable).
     * Major risks and open questions are surfaced.

10. **Single Document Owner**

    * Each design doc has one primary product owner.
    * Owner is responsible for:

      * Keeping it up to date.
      * Reflecting major changes post-implementation (or marking it obsolete).
      * Driving cross-functional alignment.
