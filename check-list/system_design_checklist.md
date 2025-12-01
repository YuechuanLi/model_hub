# Principal Engineer Design Checklist

> Use this when you pick up a product / executive design doc (PRD) and turn it into an engineering plan.

---

## 1. Inputs & Role

- [ ] I have the **product/executive design doc (PRD)** in hand.  
- [ ] I understand **who authored it** (PM, product engineer, exec).  
- [ ] I’m acting as **Principal Engineer**: owning architecture, risks, and phased delivery.  
- [ ] I’ve noted any **missing info** and will call out **assumptions** explicitly.

---

## 2. Problem & Goals

- [ ] I can restate the **problem in my own words**.  
- [ ] I listed **Product / Business goals** (user problem, target metrics).  
- [ ] I listed **System goals**:
  - [ ] Functional scope (what this system/feature will do).  
  - [ ] NFRs: latency, scale, availability, data freshness, security/privacy, cost.  
- [ ] I defined **Delivery goals**:
  - [ ] MVP / first value slice.  
  - [ ] Rough milestones (weeks/months).  
  - [ ] Required polish level (experiment vs mission-critical).  
- [ ] I wrote down **Non-goals** (what we’re not doing in this phase).

---

## 3. Context

- [ ] **Product & User Context** captured:
  - [ ] Main user journeys / flows.  
  - [ ] Traffic pattern (steady, spiky, batch, real-time).  
  - [ ] UX expectations (sub-second vs “few seconds OK”).  
- [ ] **System Context** captured:
  - [ ] Upstream/downstream systems, data sources/sinks.  
  - [ ] Compliance / data residency / vendor constraints.  
  - [ ] Legacy systems or hard constraints.  
- [ ] **Organizational Context** captured:
  - [ ] Team skills and size.  
  - [ ] Existing infra (k8s, serverless, bare metal, etc.).  
  - [ ] Observability stack (logs/metrics/traces tools).  
- [ ] I noted how context **influences design & tech choices**.

---

## 4. Guardrails ( sanity checks )

- [ ] Design favors **simplicity first** (no unnecessary microservices/complexity).  
- [ ] No **single point of failure** on critical paths.  
- [ ] APIs & data schemas have a **versioning / compatibility strategy**.  
- [ ] **Security basics** covered:
  - [ ] No hard-coded secrets.  
  - [ ] Encryption in transit & at rest where needed.  
  - [ ] Least-privilege access.  
- [ ] **Data ownership** and consistency expectations are clear.  
- [ ] I planned **logging, metrics, alerts**, and a minimal **runbook**.  
- [ ] Scope of **Phase 1** is small but **end-to-end usable**.

---

## 5. High-Level Architecture (before tech stack)

- [ ] I drew / described the **overall architecture**:
  - [ ] Major components/services.  
  - [ ] Data flows (sync vs async).  
  - [ ] State/storage locations.  
- [ ] I identified:
  - [ ] Read vs write paths.  
  - [ ] Hot (latency-sensitive) vs cold (batch/offline) paths.  
  - [ ] Key failure modes and how they’re handled.

---

## 6. Alternatives & Trade-offs

- [ ] I considered **at least two viable architecture options** (where meaningful).  
- [ ] For each option, I compared:
  - [ ] Complexity.  
  - [ ] Performance / scalability.  
  - [ ] Time-to-market.  
  - [ ] Operational burden.  
  - [ ] Cost.  
- [ ] I chose a **recommended option** and explained **why** (relative to product/exec priorities).

---

## 7. Tech Stack & Tools (after architecture)

- [ ] I chose:
  - [ ] Languages & frameworks.  
  - [ ] API style (REST/gRPC/WebSocket, etc.).  
  - [ ] Data stores (SQL/NoSQL/OLAP/cache).  
  - [ ] Messaging/streaming (if needed).  
  - [ ] Deployment/infra & CI/CD approach.  
- [ ] Choices align with:
  - [ ] Team skills & existing platform.  
  - [ ] NFRs and cost constraints.  
  - [ ] Company standards / strategic preferences.

---

## 8. Sub-component Design

For each major component:

- [ ] I defined a clear **responsibility** (single purpose).  
- [ ] I specified **public interfaces**:
  - [ ] APIs: endpoints + key fields + error model.  
  - [ ] Events/messages: schema + producers/consumers.  
- [ ] I outlined **data models** and indexing strategy.  
- [ ] I defined **failure handling** (timeouts, retries, idempotency, fallbacks).

---

## 9. Data, Observability, Security & Rollout

- [ ] **Data flow** is clear end-to-end (creation → transform → storage → consumption).  
- [ ] I identified key **metrics, logs, traces** and **dashboards** to build.  
- [ ] I defined **basic alert rules** (error rate, latency, saturation, anomalies).  
- [ ] I specified **authn/authz** model and data classification (PII/PHI/payment).  
- [ ] I defined **tenant isolation** / audit logging if needed.  
- [ ] I planned **rollout & migration**:
  - [ ] Feature flags / canary / staged rollout.  
  - [ ] Data migration strategy (if required).  
  - [ ] Clear rollback paths.

---

## 10. Risks, Assumptions & Open Questions

- [ ] I listed top **risks** with mitigation ideas.  
- [ ] I captured explicit **assumptions**, especially where the product/executive doc is vague.  
- [ ] I wrote down **open questions** that need answers from:
  - [ ] Product / PM.  
  - [ ] Executives.  
  - [ ] Other engineering teams.

