"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`.

        Synthesize a clear response with citations or source references.
        """

        source_list = "\n".join(
            f"[{index}] {source.title} ({source.url}): {source.snippet}"
            for index, source in enumerate(state.sources, start=1)
        )
        system_prompt = (
            "You are the Writer agent in a multi-agent research workflow. "
            "Write a clear final answer for technical learners. Use source markers "
            "like [1] and avoid unsupported claims."
        )
        user_prompt = (
            f"User query:\n{state.request.query}\n\n"
            f"Research notes:\n{state.research_notes or 'None'}\n\n"
            f"Analysis notes:\n{state.analysis_notes or 'None'}\n\n"
            f"Sources:\n{source_list or 'No sources'}\n\n"
            "Write the final answer with a short conclusion and cited claims."
        )

        with trace_span("writer.run", {"source_count": len(state.sources)}) as span:
            response = self.llm_client.complete(system_prompt, user_prompt)
            state.final_answer = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )
        )
        state.add_trace_event(
            "writer.final_answer",
            {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "duration_seconds": span["duration_seconds"],
            },
        )
        return state
