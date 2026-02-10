# 48-Hour Sprint Checklist

**Project:** Prompt Runner v2.0 — Production Agent Platform  
**Goal:** Deterministic demo + integration-ready production architecture  
**Timeline:** 48 hours (Jan 15-16, 2026)  
**Status:** IN PROGRESS

---

## DAY 1 (January 15) — Deterministic Demo Mode

### Morning (4-5 hours)

- [x] **1.1 Create Schema Contracts**
  - [x] `schemas/contract.json` — Formal I/O spec
  - [x] `schemas/run_schema.json` — Agent sequence
  - [x] `schemas/demo_run.json` — Golden reference
  - ⏱️ Time: 1 hour

- [x] **1.2 Build BaseAgent Framework**
  - [x] `core/agent.py` — BaseAgent interface + registry
  - [x] AgentOutput wrapper class
  - [x] @agent decorator for auto-registration
  - ⏱️ Time: 1.5 hours

- [x] **1.3 Create run_demo.py**
  - [x] Deterministic runner
  - [x] Golden file validation
  - [x] Output schema enforcement
  - [x] Logging and reporting
  - ⏱️ Time: 1.5 hours

### Afternoon (3-4 hours)

- [x] **1.4 Create Agent Template**
  - [x] `agents/agent_template.py` — Copy-paste template
  - [x] Input/output schema examples
  - [x] Usage example
  - ⏱️ Time: 0.5 hours

- [ ] **1.5 Refactor Core Agents**
  - [ ] Refactor `parsing_agent.py` to inherit BaseAgent
  - [ ] Refactor `compliance_pipeline.py` integration
  - [ ] Register in AgentRegistry
  - ⏱️ Time (estimate): 2 hours

- [ ] **1.6 Test run_demo.py**
  - [ ] Run locally: `python run_demo.py`
  - [ ] Verify golden validation passes
  - [ ] Generate demo output files
  - [ ] Check geometry `.glb` generated
  - ⏱️ Time (estimate): 1 hour

**End of Day 1 Target:** ✅ `python run_demo.py` works, produces golden output

---

## DAY 2 (January 16) — Production Platform

### Morning (3-4 hours)

- [ ] **2.1 Reorganize Folder Structure**
  - [ ] Verify `/core` has agent.py
  - [ ] Verify `/schemas` has contracts
  - [ ] Create `/storage` (symlink or reorganize db layer)
  - [ ] Ensure `/agents`, `/api`, `/tests` are clean
  - ⏱️ Time (estimate): 1 hour

- [ ] **2.2 Refactor Remaining Agents**
  - [ ] Update 2-3 more agents to inherit BaseAgent
  - [ ] Update agent registry with all agents
  - [ ] Test agent discovery: `AgentRegistry.list_agents()`
  - ⏱️ Time (estimate): 1.5 hours

- [x] **2.3 Create Integration Contracts**
  - [x] `INTEGRATION_CONTRACTS.md` (done Day 1)
  - [x] API examples for AI Platform, TTS/TTV, InsightFlow
  - [x] Versioning strategy
  - [x] Error codes + trace_id guarantee
  - ⏱️ Time: 1 hour

### Afternoon (3-4 hours)

- [ ] **2.4 Create Production Documentation**
  - [ ] `PRODUCTION_ARCHITECTURE.md` — Folder structure + design decisions
  - [ ] `API_CONTRACTS.md` — API endpoint reference
  - [ ] `VERSIONING.md` — Agent versioning strategy
  - [ ] `.env.example` — Required environment variables
  - ⏱️ Time (estimate): 1 hour

- [ ] **2.5 Pin Dependencies**
  - [ ] Verify `requirements.txt` has exact versions (e.g., `package==1.2.3`)
  - [ ] Create `requirements-dev.txt` for dev dependencies
  - [ ] Document Python version requirement (3.11+)
  - ⏱️ Time (estimate): 0.5 hours

- [ ] **2.6 Final Testing & Push**
  - [ ] Run `python run_demo.py` (must pass)
  - [ ] Run full test suite: `pytest tests/`
  - [ ] Commit all changes: `git add . && git commit -m "Production: Demo + Agent Platform v2.0"`
  - [ ] Push to GitHub: `git push origin main`
  - [ ] Verify CI passes on GitHub Actions
  - ⏱️ Time (estimate): 1 hour

**End of Day 2 Target:** ✅ Production-ready repo with extensible agent platform

---

## Definition of Done (DoD)

### Deterministic Demo (Day 1)
- [ ] `python run_demo.py` produces identical output every run
- [ ] Golden file validation passes
- [ ] All environment variables documented
- [ ] No external dependencies (everything mocked)
- [ ] README explains reproduction steps
- [ ] CI/CD example provided

### Production Platform (Day 2)
- [ ] BaseAgent interface fully implemented
- [ ] 2+ agents refactored to inherit BaseAgent
- [ ] Agent registry functional + tested
- [ ] Schema contracts locked in `schemas/`
- [ ] Integration contracts documented
- [ ] Folder structure clean and organized
- [ ] All dependencies pinned
- [ ] Handover docs complete
- [ ] GitHub push successful with CI validation

---

## What NOT to Do (Anti-goals)

❌ Don't refactor all agents now (too slow)  
❌ Don't change API schemas (break contracts)  
❌ Don't add new features (focus on structure)  
❌ Don't lose existing functionality  
❌ Don't generate timestamps that change per run (use fixed)  

---

## Failure Criteria

If ANY of these fail, sprint is blocked:

1. ❌ `python run_demo.py` does not pass validation
2. ❌ Golden file comparison fails
3. ❌ Tests fail after refactoring
4. ❌ Git push fails (cannot merge)
5. ❌ CI/CD workflow fails on GitHub

---

## Success Metrics

✅ Sprint complete if:

1. ✅ `python run_demo.py` works consistently
2. ✅ Output matches `schemas/demo_run.json`
3. ✅ All tests pass (189+ passing)
4. ✅ Code pushed to GitHub + CI green
5. ✅ Agent template allows new agents in < 10 min
6. ✅ Integration contracts enable external integration

---

## Quick Reference: Key Files Created

| File | Purpose | Size |
|------|---------|------|
| `core/agent.py` | BaseAgent interface + registry | 250 lines |
| `schemas/contract.json` | I/O specification | 150 lines |
| `schemas/run_schema.json` | Agent sequence | 80 lines |
| `schemas/demo_run.json` | Golden reference | 100 lines |
| `run_demo.py` | Deterministic runner | 200 lines |
| `INTEGRATION_CONTRACTS.md` | Integration guide | 300 lines |
| `DEMO_README.md` | Reproduction guide | 250 lines |
| `agents/agent_template.py` | Agent template | 100 lines |

**Total New Content:** ~1,400 lines of production code + documentation

---

## Handoff Checklist

Before marking sprint complete:

- [ ] All files committed to GitHub
- [ ] CI/CD pipeline passing
- [ ] Demo runs successfully on a clean machine
- [ ] Documentation is clear and actionable
- [ ] Agent template is easy to copy/modify
- [ ] Integration contracts are unambiguous
- [ ] No breaking changes to existing APIs
- [ ] Requirements.txt is pinned

---

## Contact / Questions

If stuck:
1. Check `DEMO_README.md` for troubleshooting
2. Review `schemas/contract.json` for spec questions
3. Check `core/agent.py` for BaseAgent usage
4. Refer to `agents/agent_template.py` for new agent examples
