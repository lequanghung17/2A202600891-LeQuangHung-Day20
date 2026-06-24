"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route.

        Routing policy:
        - collect research first,
        - analyze after research,
        - write after analysis,
        - stop when a final answer exists or max iterations is reached.
        """

        if state.iteration >= self.settings.max_iterations:
            next_route = "done"
            reason = "max_iterations_reached"
            if state.final_answer is None:
                state.final_answer = (
                    "Workflow stopped before completion because the max iteration guardrail "
                    "was reached."
                )
        elif not state.research_notes:
            next_route = "researcher"
            reason = "missing_research_notes"
        elif not state.analysis_notes:
            next_route = "analyst"
            reason = "missing_analysis_notes"
        elif not state.final_answer:
            next_route = "writer"
            reason = "missing_final_answer"
        else:
            next_route = "done"
            reason = "complete"

        state.record_route(next_route)
        state.agent_results.append(
            AgentResult(
                agent=AgentName.SUPERVISOR,
                content=f"Route to {next_route}: {reason}",
                metadata={"next_route": next_route, "reason": reason},
            )
        )
        state.add_trace_event(
            "supervisor.route",
            {
                "next": next_route,
                "reason": reason,
                "iteration": state.iteration,
                "max_iterations": self.settings.max_iterations,
            },
        )
        return state
