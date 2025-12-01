# Daily Review Checklist – Critical Product & Engineering Reviewer

## 0. Setup & Context
- [ ] I’ve identified **what I’m reviewing today** (feature / PR / milestone).
- [ ] I’ve skimmed the **roadmap** and noted the relevant milestone.
- [ ] I’ve opened the **product spec, design doc, and code/tests**.
- [ ] I’ve written down any **explicit Assumptions** I need to make.

---

## 1. Roadmap Alignment
- [ ] Does this work clearly map to a **roadmap item / milestone**?
- [ ] Are there signs of **scope creep** or “nice-to-haves” not in the roadmap?
- [ ] Is anything **promised in the roadmap** missing in this implementation?
- [ ] If I see divergence, I’ve noted it as a **Roadmap Risk** (not silently ignored).

---

## 2. Product & UX Check
- [ ] I can describe the **primary user journey** for this change in 2–3 sentences.
- [ ] There is a **clear, testable acceptance criteria** for the core flow.
- [ ] Happy path feels **simple and obvious** for the target user.
- [ ] At least the main **error/failure states** are defined (copy, UI behavior).
- [ ] No obvious **UX gaps**: loading/empty states, permissions, edge input.
- [ ] I’ve flagged any confusing UX as **Product/UX TODOs**, not just comments.

---

## 3. Software / System Design Check
- [ ] Responsibilities are **well-scoped** (no god objects / god services).
- [ ] The design fits the **existing architecture and tech stack** (no random new patterns).
- [ ] Data contracts/APIs are **clear and stable enough** for others to depend on.
- [ ] Basic **security & privacy** are respected (authz, validation, no obvious leaks).
- [ ] There is some **observability**: logs/metrics around critical paths.
- [ ] I have **not** suggested large refactors unless there is a real, concrete risk.

---

## 4. Code Review Check
- [ ] Core logic is **correct** for normal and edge inputs (I walked through it mentally).
- [ ] Code is **readable**: reasonable naming, small functions, clear flow.
- [ ] There is no obvious **duplication** where a helper/utility would be better.
- [ ] Error handling is **explicit** and doesn’t silently swallow important failures.
- [ ] Logs (if any) are **useful, not noisy** (no secrets, no debug spam).
- [ ] Style comments are limited to things that **truly affect clarity or consistency**.

---

## 5. Tests & Quality Check
- [ ] There is a **clear test strategy**: what’s covered by unit vs integration vs E2E.
- [ ] At least the **core happy path** is tested somewhere (unit/integration/E2E).
- [ ] At least 1–2 **important failure/edge cases** have tests.
- [ ] Tests assert **meaningful outcomes**, not only “no exception thrown”.
- [ ] No obvious sources of **flakiness** (timing sleeps, random, real network etc.).
- [ ] I’ve listed **missing test cases** as concrete TODOs (not just “add more tests”).

---

## 6. Risks, Decisions, and Tradeoffs
- [ ] I’ve written down **Key Risks** (technical, product, schedule) in plain language.
- [ ] Any **non-trivial tradeoff or decision** is captured as a short note (why we chose X).
- [ ] I’ve checked that risks don’t contradict **roadmap expectations** (timeline, scope).

---

## 7. TODO List & Handoff
- [ ] I’ve produced a **small, prioritized TODO list** (P0/P1/P2) for Product + Eng.
- [ ] Each TODO is **specific and actionable** (what, where, why).
- [ ] P0 items are clearly marked as **blocking** for release/milestone.
- [ ] Optional: I’ve added a short **summary comment** for the team (1–3 bullet points).

> If all P0s are addressed and main flows are sane, I explicitly state:  
> “From my review perspective, this is acceptable to move forward for this milestone.”
