"""Search client abstraction for ResearcherAgent."""

from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Provider-agnostic search client skeleton."""

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        This lab implementation uses a deterministic local mock corpus so the
        workflow can be benchmarked without an external search API.
        """

        query_terms = {term.lower().strip(".,:;!?()[]") for term in query.split()}
        ranked = sorted(
            _MOCK_CORPUS,
            key=lambda source: _score_source(source, query_terms),
            reverse=True,
        )
        selected = ranked[:max_results]
        return [
            source.model_copy(update={"metadata": {**source.metadata, "rank": index + 1}})
            for index, source in enumerate(selected)
        ]


def _score_source(source: SourceDocument, query_terms: set[str]) -> int:
    haystack = f"{source.title} {source.snippet}".lower()
    return sum(1 for term in query_terms if term and term in haystack)


_MOCK_CORPUS = [
    SourceDocument(
        title="GraphRAG overview",
        url="mock://sources/graphrag-overview",
        snippet=(
            "GraphRAG combines retrieval-augmented generation with graph-structured "
            "indexes so answers can use entity relationships and community summaries."
        ),
        metadata={"source_type": "mock", "topic": "GraphRAG"},
    ),
    SourceDocument(
        title="GraphRAG trade-offs",
        url="mock://sources/graphrag-tradeoffs",
        snippet=(
            "Graph-based retrieval can improve global questions and synthesis, but it "
            "adds indexing cost, graph maintenance work, and evaluation complexity."
        ),
        metadata={"source_type": "mock", "topic": "GraphRAG"},
    ),
    SourceDocument(
        title="Agent orchestration patterns",
        url="mock://sources/agent-orchestration",
        snippet=(
            "A supervisor can route work among specialized agents, inspect shared state, "
            "and stop when research, analysis, and writing outputs are complete."
        ),
        metadata={"source_type": "mock", "topic": "multi-agent"},
    ),
    SourceDocument(
        title="Multi-agent workflow guardrails",
        url="mock://sources/agent-guardrails",
        snippet=(
            "Production agent workflows need max iterations, timeouts, validation, retry "
            "policies, fallbacks, and trace logs for debugging failure modes."
        ),
        metadata={"source_type": "mock", "topic": "guardrails"},
    ),
    SourceDocument(
        title="Single-agent vs multi-agent benchmark",
        url="mock://sources/agent-benchmark",
        snippet=(
            "Useful benchmark dimensions include latency, estimated token cost, quality, "
            "citation coverage, and failure rate across the same evaluation queries."
        ),
        metadata={"source_type": "mock", "topic": "benchmark"},
    ),
    SourceDocument(
        title="Research assistant design notes",
        url="mock://sources/research-assistant-design",
        snippet=(
            "Research assistants should separate evidence collection, reasoning, and final "
            "writing when tasks require traceable handoffs and source-grounded synthesis."
        ),
        metadata={"source_type": "mock", "topic": "research-assistant"},
    ),
]
