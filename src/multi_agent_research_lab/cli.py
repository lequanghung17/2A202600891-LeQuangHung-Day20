"""Command-line entrypoint for the lab starter."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a minimal single-agent baseline."""

    _init()
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    search_client = SearchClient()
    llm_client = LLMClient()

    with trace_span("baseline.run", {"query": query}) as span:
        sources = search_client.search(query, request.max_sources)
        state.sources = sources
        source_notes = "\n".join(
            f"[{index}] {source.title}: {source.snippet}"
            for index, source in enumerate(sources, start=1)
        )
        response = llm_client.complete(
            system_prompt=(
                "You are a single-agent research assistant. Use the provided mock sources, "
                "answer clearly, and cite source markers like [1]."
            ),
            user_prompt=(
                f"User query:\n{query}\n\n"
                f"Sources:\n{source_notes}\n\n"
                "Write a concise, source-grounded answer."
            ),
        )
        state.final_answer = response.content

    state.agent_results.append(
        AgentResult(
            agent=AgentName.WRITER,
            content=state.final_answer,
            metadata={
                "mode": "single-agent-baseline",
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
    )
    state.add_trace_event(
        "baseline.complete",
        {
            "source_count": len(state.sources),
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "duration_seconds": span["duration_seconds"],
        },
    )
    console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline"))
    console.print(state.model_dump_json(indent=2))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except AgentExecutionError as exc:
        console.print(Panel.fit(str(exc), title="Execution Error", style="red"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
