"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        Extract key claims, compare viewpoints, and flag weak evidence.
        """

        research_notes = state.research_notes or "No research notes were collected."
        system_prompt = (
            "You are the Analyst agent in a multi-agent research workflow. "
            "Turn research notes into concise, source-grounded analysis. "
            "Keep citations like [1] when referring to evidence."
        )
        user_prompt = (
            f"User query:\n{state.request.query}\n\n"
            f"Research notes:\n{research_notes}\n\n"
            "Return:\n"
            "1. Key claims\n"
            "2. Trade-offs or disagreements\n"
            "3. Evidence gaps or risks\n"
            "4. Recommendation for the writer"
        )

        with trace_span("analyst.run", {"source_count": len(state.sources)}) as span:
            response = self.llm_client.complete(system_prompt, user_prompt)
            state.analysis_notes = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=state.analysis_notes,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )
        )
        state.add_trace_event(
            "analyst.analyze",
            {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "duration_seconds": span["duration_seconds"],
            },
        )
        return state
