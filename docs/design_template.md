# Design Template

## Problem

Build a research assistant that answers a user query about AI/system design by
collecting source snippets, analyzing trade-offs, and writing a final
source-grounded answer. The lab query used for the benchmark is:

```text
Compare single-agent and multi-agent workflows for customer support
```

The system must also expose a trace so reviewers can explain which agent did
what, how long each step took, and where failures would be handled.

## Why multi-agent?

A single-agent baseline is simpler and faster, but it mixes search, reasoning,
and writing into one opaque step. That makes the output harder to debug and the
handoff logic impossible to inspect.

The multi-agent workflow separates responsibilities:

- Researcher collects and formats evidence.
- Analyst extracts claims, trade-offs, risks, and evidence gaps.
- Writer turns the analysis into a final answer with citations.
- Supervisor routes the workflow and stops it safely.

This design is useful when the task needs explainability, traceable handoffs,
source grounding, and explicit failure handling.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Inspect shared state, select the next route, enforce max iterations, and stop when complete. | `ResearchState` with query, notes, answer, iteration count, errors. | Next route in `route_history`, trace event `supervisor.route`. | Bad routing can skip an agent or loop forever; max iteration guard stops this. |
| Researcher | Retrieve mock sources and create concise research notes with citation markers. | User query and `max_sources`. | `sources`, `research_notes`, trace event `researcher.search`. | Mock corpus may not cover the query; fallback stores minimal research notes. |
| Analyst | Convert research notes into structured claims, trade-offs, evidence gaps, and writer recommendations. | Query, `research_notes`, source count. | `analysis_notes`, token metadata, trace event `analyst.analyze`. | LLM call may timeout or produce weak analysis; retry and fallback handle this. |
| Writer | Produce the final source-grounded answer for technical learners. | Query, sources, `research_notes`, `analysis_notes`. | `final_answer`, token metadata, trace event `writer.final_answer`. | Final answer may miss citations or overstate evidence; validation can be added before returning. |

## Shared state

| Field | Purpose |
|---|---|
| `request` | Stores the original `ResearchQuery`, including query text, audience, and max source count. |
| `iteration` | Counts Supervisor routing decisions and supports the max-iteration guardrail. |
| `route_history` | Records the path selected by Supervisor, for example `researcher -> analyst -> writer -> done`. |
| `sources` | Stores `SourceDocument` items returned by the mock search client. |
| `research_notes` | Stores Researcher output with numbered source markers. |
| `analysis_notes` | Stores Analyst output: claims, trade-offs, gaps, and recommendations. |
| `final_answer` | Stores Writer output returned to the user. |
| `agent_results` | Stores each agent's content and metadata, including token usage. |
| `trace` | Stores structured trace events for routing, search, analysis, writing, retries, and fallback. |
| `errors` | Stores recoverable execution errors and retry/fallback details. |

## Routing policy

The current workflow is deterministic and state-driven:

```text
User query
  |
  v
Supervisor
  |-- if research_notes missing --> Researcher
  |-- if analysis_notes missing --> Analyst
  |-- if final_answer missing ----> Writer
  |-- otherwise ------------------> done
```

Expected route for a normal run:

```text
researcher -> analyst -> writer -> done
```

The workflow implementation calls Supervisor before each worker so the trace
shows every handoff. Worker internals stay inside `agents/`; orchestration,
retry, and fallback stay inside `graph/workflow.py`.

## Guardrails

- Max iterations: `MAX_ITERATIONS=6` from `.env`; Supervisor routes to `done`
  when the limit is reached.
- Timeout: OpenAI client timeout uses `TIMEOUT_SECONDS=60` from `.env`.
- Retry: `LLMClient` retries failed OpenAI calls up to three times; workflow
  execution retries each agent once before fallback.
- Fallback: Researcher can store fallback notes, Analyst can pass research
  notes forward, and Writer can return a fallback answer based on available
  research notes.
- Validation: Current validation is schema-based through Pydantic models and
  route/state checks. Recommended next validation is citation checking: every
  cited marker in `final_answer` should exist in `state.sources`.

## Benchmark plan

| Query | Runs | Metrics | Expected outcome |
|---|---:|---|---|
| `Compare single-agent and multi-agent workflows for customer support` | 1 baseline, 1 multi-agent | Latency, input tokens, output tokens, total tokens, quality score, citation coverage, failure rate. | Baseline should be faster and cheaper; multi-agent should be more structured and easier to debug. |

Benchmark result from this lab run:

| Run | Latency (s) | Total Tokens | Quality | Citation Coverage | Failure Rate |
|---|---:|---:|---:|---:|---:|
| Single-agent baseline | 8.00 | 571 | 7.5/10 | 5/5 sources cited | 0/1 |
| Multi-agent workflow | 18.07 | 2,093 | 8.5/10 | 5/5 sources cited | 0/1 |

The multi-agent workflow was slower and used more tokens, but produced a
clearer trace and a more structured answer. The detailed benchmark write-up is
in `reports/benchmark_report.md`.
