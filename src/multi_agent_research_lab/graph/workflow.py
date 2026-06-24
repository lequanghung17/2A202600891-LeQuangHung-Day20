"""LangGraph workflow skeleton."""

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        llm_client = LLMClient(self.settings)
        search_client = SearchClient()
        self.supervisor = SupervisorAgent(self.settings)
        self.agents: dict[str, BaseAgent] = {
            "researcher": ResearcherAgent(search_client),
            "analyst": AnalystAgent(llm_client),
            "writer": WriterAgent(llm_client),
        }

    def build(self) -> dict[str, BaseAgent]:
        """Return workflow nodes for this lab implementation.

        The workflow uses the same graph shape requested by the lab guide:
        supervisor -> researcher -> supervisor -> analyst -> supervisor -> writer.
        A plain Python loop keeps the trace easy to inspect for the assignment.
        """

        return {"supervisor": self.supervisor, **self.agents}

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state.

        Supervisor owns routing. This method owns execution, retry, and fallback.
        """

        for _ in range(self.settings.max_iterations + 1):
            state = self.supervisor.run(state)
            route = state.route_history[-1]
            if route == "done":
                return state

            agent = self.agents.get(route)
            if agent is None:
                raise AgentExecutionError(f"Unknown route selected by supervisor: {route}")
            state = self._run_agent_with_retry(agent, state)

        state.errors.append("Workflow stopped because the execution loop guardrail was reached.")
        state.add_trace_event(
            "workflow.guardrail",
            {"reason": "execution_loop_guardrail", "max_iterations": self.settings.max_iterations},
        )
        if state.final_answer is None:
            state.final_answer = "Workflow stopped before a final answer was produced."
        return state

    def _run_agent_with_retry(self, agent: BaseAgent, state: ResearchState) -> ResearchState:
        for attempt in range(1, 3):
            try:
                return agent.run(state)
            except Exception as exc:
                state.errors.append(f"{agent.name} attempt {attempt} failed: {exc}")
                state.add_trace_event(
                    "workflow.retry",
                    {"agent": agent.name, "attempt": attempt, "error": str(exc)},
                )

        return self._apply_fallback(agent.name, state)

    def _apply_fallback(self, agent_name: str, state: ResearchState) -> ResearchState:
        if agent_name == "researcher":
            state.research_notes = "Researcher fallback: no sources were available."
        elif agent_name == "analyst":
            state.analysis_notes = "Analyst fallback: use research notes directly."
        elif agent_name == "writer":
            state.final_answer = (
                "Writer fallback: unable to call the LLM after retries. "
                f"Research notes: {state.research_notes or 'none'}"
            )
        else:
            raise AgentExecutionError(f"No fallback registered for agent: {agent_name}")

        state.add_trace_event("workflow.fallback", {"agent": agent_name})
        return state
