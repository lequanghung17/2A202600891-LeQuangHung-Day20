"""Researcher agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient | None = None) -> None:
        self.search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`.

        Search is backed by a local mock corpus for this lab submission.
        """

        with trace_span("researcher.run", {"query": state.request.query}) as span:
            sources = self.search_client.search(state.request.query, state.request.max_sources)
            state.sources = sources
            state.research_notes = "\n".join(
                f"[{index}] {source.title}: {source.snippet}"
                for index, source in enumerate(sources, start=1)
            )

        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes or "",
                metadata={"source_count": len(state.sources)},
            )
        )
        state.add_trace_event(
            "researcher.search",
            {
                "source_count": len(state.sources),
                "sources": [source.title for source in state.sources],
                "duration_seconds": span["duration_seconds"],
            },
        )
        return state
