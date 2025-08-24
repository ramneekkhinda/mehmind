"""
Ghost-Run Simulator: Core simulation engine for LangGraph workflows.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from ..core.budget import BudgetContext
from ..utils.logging import get_logger
from .reports import ConflictReport, GhostReport, StepReport

logger = get_logger(__name__)


@dataclass
class GhostConfig:
    """Configuration for Ghost-Run simulation."""

    budget_cap: float = 10.0
    rpm_limit: int = 60
    fail_on_conflict: bool = False
    fail_on_budget_exceeded: bool = True
    enable_cost_estimation: bool = True
    enable_conflict_detection: bool = True
    enable_policy_checking: bool = True
    max_steps: int = 100
    timeout_seconds: int = 30


@dataclass
class GhostState:
    """State tracking during ghost simulation."""

    # Execution tracking
    step_count: int = 0
    start_time: float = field(default_factory=time.time)
    current_node: Optional[str] = None

    # Cost tracking
    total_cost: float = 0.0
    total_tokens: int = 0
    llm_calls: int = 0
    api_calls: int = 0
    effects_count: int = 0

    # Conflict tracking
    resource_locks: Dict[str, str] = field(default_factory=dict)  # resource -> node
    frequency_caps: Dict[str, int] = field(default_factory=dict)  # action -> count
    budget_consumed: float = 0.0

    # Policy violations
    policy_violations: List[str] = field(default_factory=list)

    # Simulation metadata
    simulation_id: str = field(default_factory=lambda: f"ghost_{uuid.uuid4().hex[:8]}")
    original_state: Dict[str, Any] = field(default_factory=dict)


class GhostSimulator:
    """
    Core simulator for Ghost-Run functionality.

    Intercepts LangGraph execution to provide cost estimates, conflict detection,
    and safety analysis without making actual external calls.
    """

    def __init__(self, config: Optional[GhostConfig] = None):
        """Initialize the ghost simulator."""
        self.config = config or GhostConfig()
        self.steps: List[StepReport] = []
        self.conflicts: List[ConflictReport] = []

    async def simulate(
        self,
        graph: StateGraph,
        input_state: Dict[str, Any],
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> GhostReport:
        """
        Simulate execution of a LangGraph workflow.

        Args:
            graph: LangGraph StateGraph to simulate
            input_state: Input state for the workflow
            initial_state: Optional initial state (merged with input_state)

        Returns:
            GhostReport with simulation results
        """
        # Initialize simulation state
        ghost_state = GhostState()
        ghost_state.original_state = input_state.copy()

        if initial_state:
            ghost_state.original_state.update(initial_state)

        # Create checkpoint saver for simulation
        memory_saver = MemorySaver()

        # Track execution
        start_time = time.time()

        try:
            # Simulate graph execution
            config = {
                "configurable": {"thread_id": f"ghost_{ghost_state.simulation_id}"}
            }

            # Get the compiled graph
            compiled_graph = graph.compile(checkpointer=memory_saver)

            # Run simulation with step-by-step tracking
            async for step in self._simulate_steps(compiled_graph, ghost_state, config):
                self.steps.append(step)

                # Check for early termination
                if self.config.fail_on_conflict and step.conflicts:
                    logger.warning(
                        f"Simulation stopped due to conflicts in step {step.step_number}"
                    )
                    break

                if self.config.fail_on_budget_exceeded and step.budget_exceeded:
                    logger.warning(
                        f"Simulation stopped due to budget exceeded in step {step.step_number}"
                    )
                    break

                if ghost_state.step_count >= self.config.max_steps:
                    logger.warning(
                        f"Simulation stopped at max steps ({self.config.max_steps})"
                    )
                    break

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            # Create error step report
            error_step = StepReport(
                step_number=ghost_state.step_count,
                node_name="error",
                duration_ms=(time.time() - start_time) * 1000,
                cost=0.0,
                tokens=0,
                conflicts=[],
                error=str(e),
            )
            self.steps.append(error_step)

        # Generate final report
        execution_time = time.time() - start_time

        return GhostReport(
            simulation_id=ghost_state.simulation_id,
            total_steps=len(self.steps),
            total_cost=ghost_state.total_cost,
            total_tokens=ghost_state.total_tokens,
            execution_time_ms=execution_time * 1000,
            llm_calls=ghost_state.llm_calls,
            api_calls=ghost_state.api_calls,
            effects_count=ghost_state.effects_count,
            steps=self.steps,
            conflicts=self.conflicts,
            policy_violations=ghost_state.policy_violations,
            budget_exceeded=ghost_state.budget_consumed > self.config.budget_cap,
            input_state=input_state,
        )

    async def _simulate_steps(
        self, compiled_graph, ghost_state: GhostState, config: Dict[str, Any]
    ):
        """Simulate execution step by step."""

        # Start with input state
        current_state = ghost_state.original_state.copy()

        # Add ghost metadata
        current_state["_ghost_mode"] = True
        current_state["_ghost_state"] = ghost_state

        # Track execution
        step_number = 0

        while step_number < self.config.max_steps:
            step_start = time.time()

            try:
                # Get next node to execute
                next_node = compiled_graph.get_next(current_state, config)

                if next_node == END:
                    logger.info("Simulation completed - reached END node")
                    break

                # Execute node with ghost interception
                result = await self._execute_node_ghost(
                    compiled_graph,
                    next_node,
                    current_state,
                    config,
                    ghost_state,
                    step_number,
                )

                # Update state
                current_state.update(result)

                # Calculate step metrics
                step_duration = (time.time() - step_start) * 1000

                # Create step report
                step_report = StepReport(
                    step_number=step_number,
                    node_name=next_node,
                    duration_ms=step_duration,
                    cost=result.get("_ghost_cost", 0.0),
                    tokens=result.get("_ghost_tokens", 0),
                    conflicts=result.get("_ghost_conflicts", []),
                    budget_exceeded=result.get("_ghost_budget_exceeded", False),
                    state_snapshot=current_state.copy(),
                )

                # Update ghost state
                ghost_state.step_count = step_number + 1
                ghost_state.total_cost += step_report.cost
                ghost_state.total_tokens += step_report.tokens

                # Track conflicts
                for conflict in step_report.conflicts:
                    self.conflicts.append(conflict)

                yield step_report

                step_number += 1

            except Exception as e:
                logger.error(f"Error in step {step_number}: {e}")
                # Create error step report
                error_step = StepReport(
                    step_number=step_number,
                    node_name="error",
                    duration_ms=(time.time() - step_start) * 1000,
                    cost=0.0,
                    tokens=0,
                    conflicts=[],
                    error=str(e),
                )
                yield error_step
                break

    async def _execute_node_ghost(
        self,
        compiled_graph,
        node_name: str,
        state: Dict[str, Any],
        config: Dict[str, Any],
        ghost_state: GhostState,
        step_number: int,
    ) -> Dict[str, Any]:
        """Execute a single node with ghost interception."""

        # Create ghost budget context
        async with BudgetContext(
            usd_cap=self.config.budget_cap - ghost_state.budget_consumed,
            rpm=self.config.rpm_limit,
        ) as _budget:  # noqa: F841
            # Intercept the node execution
            _original_state = state.copy()  # noqa: F841

            try:
                # Execute node (this will be intercepted by our ghost decorators)
                result = await compiled_graph.ainvoke(
                    {"node": node_name, "state": state}, config
                )

                # Extract ghost metrics from result
                ghost_cost = result.get("_ghost_cost", 0.0)
                ghost_tokens = result.get("_ghost_tokens", 0)
                ghost_conflicts = result.get("_ghost_conflicts", [])

                # Update ghost state
                ghost_state.budget_consumed += ghost_cost
                ghost_state.total_tokens += ghost_tokens

                # Track LLM calls
                if result.get("_ghost_llm_call"):
                    ghost_state.llm_calls += 1

                # Track API calls
                if result.get("_ghost_api_call"):
                    ghost_state.api_calls += 1

                # Track effects
                if result.get("_ghost_effect"):
                    ghost_state.effects_count += 1

                # Add ghost metadata to result
                result["_ghost_cost"] = ghost_cost
                result["_ghost_tokens"] = ghost_tokens
                result["_ghost_conflicts"] = ghost_conflicts
                result["_ghost_budget_exceeded"] = (
                    ghost_state.budget_consumed > self.config.budget_cap
                )

                return result

            except Exception as e:
                logger.error(f"Node execution failed: {e}")
                return {
                    "_ghost_cost": 0.0,
                    "_ghost_tokens": 0,
                    "_ghost_conflicts": [],
                    "_ghost_error": str(e),
                    "_ghost_budget_exceeded": False,
                }


# Convenience function for easy usage
async def ghost_run(
    graph: StateGraph,
    input_state: Dict[str, Any],
    budget_cap: float = 10.0,
    rpm_limit: int = 60,
    fail_on_conflict: bool = False,
    **kwargs,
) -> GhostReport:
    """
    Convenience function to run Ghost-Run simulation.

    Args:
        graph: LangGraph StateGraph to simulate
        input_state: Input state for the workflow
        budget_cap: Maximum budget for simulation
        rpm_limit: Requests per minute limit
        fail_on_conflict: Whether to stop on first conflict
        **kwargs: Additional GhostConfig parameters

    Returns:
        GhostReport with simulation results
    """
    config = GhostConfig(
        budget_cap=budget_cap,
        rpm_limit=rpm_limit,
        fail_on_conflict=fail_on_conflict,
        **kwargs,
    )

    simulator = GhostSimulator(config)
    return await simulator.simulate(graph, input_state)
