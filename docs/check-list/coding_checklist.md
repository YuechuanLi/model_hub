# Daily Implementation Checklist

## 1. Before Coding – Task & Context

[ ] Do I clearly understand the **ticket / feature / bug**?  
[ ] Did I restate the **inputs, outputs, and main flows** in my own words?  
[ ] Did I review the **relevant product spec & system design**?  
[ ] Do I know which **service/module** this belongs to?  
[ ] Did I identify **non-functional requirements** (perf, reliability, security)?  

[ ] Did I check **existing code patterns** (similar endpoints, handlers, jobs)?  
[ ] Am I sure this is an **incremental change**, not a redesign?
[ ] Is the **tech stack already decided** for this service/module?
    - If yes: am I fully aligned with it (language, framework, DB, messaging)?
    - If no: did I pick a simple, mainstream stack consistent with the repo and clearly state it as a proposal?
[ ] Am I avoiding introducing new frameworks/DBs/queues unless explicitly required?


---

## 2. Design & Scope Control

[ ] Is my plan the **simplest solution** that satisfies the current spec?  
[ ] Am I **avoiding over-engineering** (no extra layers / frameworks “just in case”)?  
[ ] Am I **avoiding large-scale refactors** unless explicitly requested?  
[ ] Is my change **local and minimal diff** where possible?  

[ ] Did I outline:
  - [ ] Main functions/classes/modules  
  - [ ] Data structures / schemas touched  
  - [ ] Error-handling approach  
  - [ ] Logging/metrics points (if needed)  

---

## 3. Implementation Quality

[ ] Am I following the **project’s language, framework, and style**?  
[ ] Did I **reuse existing helpers** instead of duplicating or reinventing?  
[ ] Are functions **small, focused, and composable** (no “god” functions)?  
[ ] Did I avoid premature abstraction (only extract helpers if clearly reused or clearer)?  

[ ] Is error handling:
  - [ ] Early input validation  
  - [ ] Clear, structured errors  
  - [ ] Consistent with existing patterns  

[ ] Is observability:
  - [ ] Logs at key operations / decisions / failures  
  - [ ] Including useful IDs (request/user/resource)  
  - [ ] No sensitive data in logs  

[ ] Did I avoid:
  - [ ] Hard-coded secrets or credentials  
  - [ ] Heavy new dependencies without justification  
  - [ ] Unnecessary blocking calls on hot paths  

---

## 4. Tests & Verification

[ ] Did I add/extend **unit tests** for:
  - [ ] Normal cases  
  - [ ] Edge cases  
  - [ ] Error paths  

[ ] If applicable, did I add a **small integration/flow test** or example script?  
[ ] Can the tests run with the project’s tools (e.g. `pytest`, `go test`, `npm test`)?  
[ ] Did I actually **run the tests** and see them pass?  

[ ] Did I sanity-check performance if this is on a critical path?

---

## 5. TODOs & Documentation

[ ] Did I add **TODOs only for non-critical follow-ups**?  
[ ] Are TODOs:
  - [ ] Specific and actionable  
  - [ ] Scoped (not “TODO: refactor everything”)  
  - [ ] In a consistent format (e.g. `TODO:LEE: ...`)?  

[ ] Did I add/refresh **docstrings or comments** for:
  - [ ] Public APIs or entrypoints  
  - [ ] Non-obvious logic or constraints  

[ ] If I introduced a new subsystem / workflow:
  - [ ] Did I add a short note in `README.md` / `DESIGN.md`?  

---

## 6. Final Self-Review

[ ] Does this change **match the spec** without sneaking in extra “nice to haves”?  
[ ] Is the diff **as small as reasonably possible**?  
[ ] Would another engineer be able to **read and extend** this easily?  
[ ] Are known limitations and risks clearly **called out in notes or TODOs**?  
[ ] Am I comfortable owning this code in production if something breaks?

