# Benchmark Report

## Setup

- Date: 2026-06-24
- Query: `Compare single-agent and multi-agent workflows for customer support`
- LLM provider: OpenAI
- Search provider: local mock search corpus
- Runs per workflow: 1
- Trace artifact: terminal JSON trace from CLI output

## Summary

| Run | Latency (s) | Input Tokens | Output Tokens | Total Tokens | Quality (0-10) | Citation Coverage | Failure Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Single-agent baseline | 8.00 | 229 | 342 | 571 | 7.5 | 5/5 mock sources cited | 0/1 |
| Multi-agent workflow | 18.07 | 1,183 | 910 | 2,093 | 8.5 | 5/5 mock sources cited | 0/1 |

## Trace Summary

Trace screenshots:

- [Trace run overview](../screenshots/trace1.png)
- [Trace event details](../screenshots/trace2.png)

### Single-agent baseline

```text
baseline.complete
source_count=5
input_tokens=229
output_tokens=342
duration_seconds=8.0023
errors=[]
```

The baseline produced a complete answer in one LLM call. It cited all five mock
sources, but all tasks were handled inside one step, so the reasoning process is
less inspectable.

### Multi-agent workflow

```text
supervisor.route -> researcher
researcher.search
supervisor.route -> analyst
analyst.analyze
supervisor.route -> writer
writer.final_answer
supervisor.route -> done
errors=[]
```

Measured agent durations:

| Step | Duration (s) | Input Tokens | Output Tokens |
|---|---:|---:|---:|
| Researcher search | 0.00 | 0 | 0 |
| Analyst analyze | 9.37 | 257 | 465 |
| Writer final answer | 8.71 | 926 | 445 |
| Total measured agent time | 18.07 | 1,183 | 910 |

The multi-agent run exposed each handoff through `route_history`:

```text
researcher -> analyst -> writer -> done
```

## Quality Comparison

The single-agent baseline was faster and cheaper because it made one LLM call.
Its answer was clear and cited the mock sources, but it mixed research,
analysis, and writing into one opaque step.

The multi-agent workflow was slower and used more tokens because it made
separate LLM calls for analysis and final writing. In exchange, it produced a
more structured answer with explicit sections for workflow structure,
performance metrics, enhanced capabilities, trade-offs, evidence gaps, and
conclusion. The trace also made it easier to explain which agent did what.

## Final Answer Comparison

### Single-agent baseline answer

```text
When comparing single-agent and multi-agent workflows for customer support,
several key factors emerge:

1. Complexity and Specialization: Multi-agent workflows allow for the
orchestration of specialized agents, which can handle different aspects of
customer support more efficiently. A supervisor can route tasks among these
agents based on their expertise, leading to potentially higher quality
responses and faster resolution times [5]. In contrast, single-agent workflows
rely on one agent to manage all inquiries, which may limit the depth of
knowledge and responsiveness.

2. Performance Metrics: Benchmarks indicate that multi-agent systems may
exhibit lower latency and failure rates when compared to single-agent systems,
particularly in complex scenarios. However, they can also incur higher costs
due to the need for more tokens and the complexity of managing multiple agents
[2]. Single-agent systems might be simpler and less costly but could struggle
with more intricate queries.

3. Error Handling and Debugging: Multi-agent workflows benefit from structured
guardrails that include max iterations, timeouts, and validation processes,
which help in managing failures and debugging [1]. Single-agent systems may
lack these robust mechanisms, making them more vulnerable to errors without a
clear fallback strategy.

4. Knowledge Management: Multi-agent systems can leverage graph-based retrieval
methods, such as GraphRAG, to enhance the quality of responses by utilizing
entity relationships and community knowledge [3][4]. This capability can
significantly improve the handling of global questions and synthesis of
information, which is often a challenge for single-agent systems.

In summary, while single-agent workflows offer simplicity and lower costs,
multi-agent workflows provide enhanced specialization, better error management,
and improved performance metrics, making them more suitable for complex customer
support scenarios.
```

### Multi-agent final answer

```text
When comparing single-agent and multi-agent workflows for customer support,
several key differences and trade-offs emerge.

Workflow Structure
Single-agent workflows rely on a single entity to manage all aspects of customer
interactions. This can limit flexibility and depth of response, especially for
complex queries. In contrast, multi-agent workflows utilize multiple specialized
agents that can collaborate and share state, enhancing their ability to handle
intricate tasks and provide more nuanced responses [1][5].

Performance Metrics
Performance metrics such as latency, estimated token cost, quality of responses,
citation coverage, and failure rates are critical in evaluating these systems.
Multi-agent systems often outperform single-agent systems in these areas,
particularly when addressing complex inquiries that require specialized
knowledge [2].

Enhanced Capabilities
Multi-agent workflows can leverage advanced techniques like GraphRAG, which
employs graph-structured indexes to improve response quality by incorporating
entity relationships and community summaries. This results in richer and more
contextually relevant answers [3][4]. However, the introduction of such
techniques also adds complexity in terms of indexing costs and maintenance.

Trade-offs
While multi-agent systems can provide comprehensive responses, they introduce
additional complexity in orchestration and management, potentially leading to
higher operational costs [4][5]. Conversely, single-agent systems may be more
cost-effective and simpler to implement, but they may struggle with high volumes
of inquiries or complex queries [2].

Evidence Gaps
There are notable gaps in evidence regarding the practical challenges of
implementing multi-agent systems in real-world customer support scenarios,
particularly concerning agent interaction management and orchestration
effectiveness [1][5]. Additionally, further research is needed to assess the
long-term performance and scalability of these systems in dynamic environments
[2].

Conclusion
In summary, while multi-agent workflows offer enhanced capabilities and improved
performance metrics for complex customer support tasks, they also come with
increased complexity and potential operational challenges. Organizations must
weigh these trade-offs carefully when deciding between single-agent and
multi-agent systems for their customer support needs.

Sources:
[1] Multi-agent workflow guardrails.
[2] Single-agent vs multi-agent benchmark.
[3] GraphRAG overview.
[4] GraphRAG trade-offs.
[5] Agent orchestration patterns.
```

### Comparison notes

The baseline answer is shorter and more direct. It is useful for a quick
overview, but it makes some broad claims inside one generated step.

The multi-agent answer is more structured and easier to audit because the final
response is supported by a separate `research_notes` step and a separate
`analysis_notes` step. It also includes an explicit evidence-gap section, which
makes limitations clearer for peer review.

## Citation Coverage

Both workflows used the same five mock sources:

1. Multi-agent workflow guardrails
2. Single-agent vs multi-agent benchmark
3. GraphRAG overview
4. GraphRAG trade-offs
5. Agent orchestration patterns

Both final answers referenced all five source markers. For this lab run,
citation coverage is therefore counted as `5/5` provided mock sources cited.

## Cost Notes

Exact USD cost was not calculated by the app. Token usage was recorded instead:

- Baseline: `571` total tokens
- Multi-agent: `2,093` total tokens

The multi-agent workflow used about `3.7x` more tokens than the baseline in this
single run.

## Failure Mode

A realistic failure mode is an LLM timeout or API error during the Analyst or
Writer step. If that happens, the workflow can stop before producing
`analysis_notes` or `final_answer`, or it can produce a low-quality fallback
answer.

Another failure mode is weak citation grounding: the Writer may cite a source
marker even when the claim is only loosely supported by the mock source snippet.
This is especially likely because the mock corpus is small.

## Fix

The implementation includes the following guardrails:

- `MAX_ITERATIONS=6` prevents the supervisor loop from running forever.
- OpenAI calls use timeout settings from `.env`.
- LLM calls are retried up to three times in `LLMClient`.
- Workflow execution retries each agent once before fallback.
- The workflow records trace events for route decisions, agent execution,
  token usage, duration, retries, and fallback.

Recommended next improvement: add a validation step before returning
`final_answer` that checks whether every cited marker exists in `state.sources`
and whether at least one citation appears in each major claim section.

## Conclusion

For this query, the multi-agent workflow produced a more explainable and
structured result, but it cost more time and tokens. The baseline is preferable
for simple customer support comparisons where speed matters most. The
multi-agent workflow is preferable when the task needs traceable handoffs,
explicit analysis, and easier debugging.
