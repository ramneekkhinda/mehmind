"""
Tests for Ghost-Run functionality.
"""

import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from meshmind.ghost import GhostSimulator, GhostConfig, ghost_run, GhostReport
from meshmind.ghost.reports import ConflictReport, StepReport
from meshmind.ghost.decorators import (
    _estimate_tokens, 
    _estimate_llm_cost,
    _check_resource_locks,
    _check_frequency_caps,
    _check_idempotency_conflicts
)


class TestGhostConfig:
    """Test GhostConfig functionality."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = GhostConfig()
        
        assert config.budget_cap == 10.0
        assert config.rpm_limit == 60
        assert config.fail_on_conflict is False
        assert config.fail_on_budget_exceeded is True
        assert config.enable_cost_estimation is True
        assert config.enable_conflict_detection is True
        assert config.enable_policy_checking is True
        assert config.max_steps == 100
        assert config.timeout_seconds == 30
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = GhostConfig(
            budget_cap=5.0,
            rpm_limit=30,
            fail_on_conflict=True,
            max_steps=50
        )
        
        assert config.budget_cap == 5.0
        assert config.rpm_limit == 30
        assert config.fail_on_conflict is True
        assert config.max_steps == 50


class TestGhostSimulator:
    """Test GhostSimulator functionality."""
    
    def test_simulator_initialization(self):
        """Test simulator initialization."""
        config = GhostConfig(budget_cap=5.0)
        simulator = GhostSimulator(config)
        
        assert simulator.config.budget_cap == 5.0
        assert len(simulator.steps) == 0
        assert len(simulator.conflicts) == 0
    
    @pytest.mark.asyncio
    async def test_simulate_with_mock_graph(self):
        """Test simulation with a mock LangGraph."""
        # Create a mock graph
        mock_graph = Mock()
        mock_compiled_graph = Mock()
        mock_graph.compile.return_value = mock_compiled_graph
        
        # Mock the simulation steps to avoid LangGraph API issues
        simulator = GhostSimulator()
        
        async def mock_async_generator():
            yield StepReport(
                step_number=0,
                node_name="test_node",
                duration_ms=100.0,
                cost=0.01,
                tokens=100,
                conflicts=[],
                budget_exceeded=False
            )
        
        with patch.object(simulator, '_simulate_steps') as mock_simulate:
            mock_simulate.return_value = mock_async_generator()
            
            input_state = {"test": "data"}
            report = await simulator.simulate(mock_graph, input_state)
            
            assert isinstance(report, GhostReport)
            assert report.total_steps == 1
            # The simulator should have accumulated the cost from the step
            assert len(report.steps) == 1
            assert report.steps[0].cost == 0.01
            assert report.input_state == input_state


class TestGhostReport:
    """Test GhostReport functionality."""
    
    def test_report_creation(self):
        """Test creating a ghost report."""
        steps = [
            StepReport(
                step_number=0,
                node_name="node1",
                duration_ms=50.0,
                cost=0.005,
                tokens=50,
                conflicts=[]
            ),
            StepReport(
                step_number=1,
                node_name="node2", 
                duration_ms=75.0,
                cost=0.010,
                tokens=100,
                conflicts=[]
            )
        ]
        
        report = GhostReport(
            simulation_id="test_123",
            total_steps=2,
            total_cost=0.015,
            total_tokens=150,
            execution_time_ms=125.0,
            llm_calls=2,
            api_calls=0,
            effects_count=0,
            steps=steps,
            conflicts=[],
            policy_violations=[],
            budget_exceeded=False,
            input_state={"test": "data"}
        )
        
        assert report.simulation_id == "test_123"
        assert report.total_cost == 0.015
        assert report.total_tokens == 150
        assert len(report.steps) == 2
    
    def test_report_summary(self):
        """Test report summary generation."""
        report = GhostReport(
            simulation_id="test_123",
            total_steps=1,
            total_cost=0.01,
            total_tokens=100,
            execution_time_ms=50.0,
            llm_calls=1,
            api_calls=0,
            effects_count=0,
            steps=[],
            conflicts=[],
            policy_violations=[],
            budget_exceeded=False,
            input_state={}
        )
        
        summary = report.get_summary()
        
        assert summary["simulation_id"] == "test_123"
        assert summary["total_cost"] == 0.01
        assert summary["success"] is True
        assert summary["conflicts_count"] == 0
    
    def test_cost_breakdown(self):
        """Test cost breakdown calculation."""
        steps = [
            StepReport(0, "node1", 50.0, 0.005, 50, []),
            StepReport(1, "node2", 75.0, 0.010, 100, []),
            StepReport(2, "node1", 25.0, 0.003, 30, [])  # Same node again
        ]
        
        report = GhostReport(
            simulation_id="test",
            total_steps=3,
            total_cost=0.018,
            total_tokens=180,
            execution_time_ms=150.0,
            llm_calls=3,
            api_calls=0,
            effects_count=0,
            steps=steps,
            conflicts=[],
            policy_violations=[],
            budget_exceeded=False,
            input_state={}
        )
        
        breakdown = report.get_cost_breakdown()
        
        assert breakdown["node1"] == 0.008  # 0.005 + 0.003
        assert breakdown["node2"] == 0.010
    
    def test_conflicts_by_type(self):
        """Test grouping conflicts by type."""
        conflicts = [
            ConflictReport("resource_lock", "res1", "node1", 0, "high", "Lock conflict"),
            ConflictReport("frequency_cap", "res2", "node2", 1, "medium", "Frequency exceeded"),
            ConflictReport("resource_lock", "res3", "node3", 2, "low", "Another lock conflict")
        ]
        
        report = GhostReport(
            simulation_id="test",
            total_steps=3,
            total_cost=0.0,
            total_tokens=0,
            execution_time_ms=100.0,
            llm_calls=0,
            api_calls=0,
            effects_count=0,
            steps=[],
            conflicts=conflicts,
            policy_violations=[],
            budget_exceeded=False,
            input_state={}
        )
        
        grouped = report.get_conflicts_by_type()
        
        assert len(grouped["resource_lock"]) == 2
        assert len(grouped["frequency_cap"]) == 1
    
    def test_json_serialization(self):
        """Test JSON serialization of report."""
        report = GhostReport(
            simulation_id="test",
            total_steps=1,
            total_cost=0.01,
            total_tokens=100,
            execution_time_ms=50.0,
            llm_calls=1,
            api_calls=0,
            effects_count=0,
            steps=[],
            conflicts=[],
            policy_violations=[],
            budget_exceeded=False,
            input_state={"test": "data"}
        )
        
        json_str = report.to_json()
        assert "test" in json_str
        assert "0.01" in json_str
        
        dict_data = report.to_dict()
        assert dict_data["simulation_id"] == "test"
        assert dict_data["total_cost"] == 0.01


class TestGhostDecorators:
    """Test Ghost-Run decorator functionality."""
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test prompt for token estimation"
        tokens = _estimate_tokens(text, max_output_tokens=500)
        
        # Should include input tokens (text length / 4) + output tokens
        expected = len(text) // 4 + 500
        assert tokens == expected
    
    def test_estimate_llm_cost(self):
        """Test LLM cost estimation."""
        # Test OpenAI GPT-3.5-turbo
        cost = _estimate_llm_cost("openai", "gpt-3.5-turbo", 1000, 500)
        expected = (1000 / 1000) * 0.0015 + (500 / 1000) * 0.002
        assert abs(cost - expected) < 0.0001
        
        # Test OpenAI GPT-4
        cost = _estimate_llm_cost("openai", "gpt-4", 1000, 500)
        expected = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
        assert abs(cost - expected) < 0.0001
        
        # Test Anthropic Claude
        cost = _estimate_llm_cost("anthropic", "claude-3-sonnet", 1000, 500)
        expected = (1000 / 1000) * 0.003 + (500 / 1000) * 0.015
        assert abs(cost - expected) < 0.0001
        
        # Test unknown provider (should default to sim)
        cost = _estimate_llm_cost("unknown", "unknown", 1000, 500)
        expected = (1000 / 1000) * 0.001 + (500 / 1000) * 0.001
        assert abs(cost - expected) < 0.0001
    
    def test_check_resource_locks(self):
        """Test resource lock conflict detection."""
        # Should detect conflict for customer resource with non-primary agent
        conflicts = _check_resource_locks("customer:123", "secondary-agent")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "resource_lock"
        
        # Should not detect conflict for primary agent
        conflicts = _check_resource_locks("customer:123", "primary-agent")
        assert len(conflicts) == 0
        
        # Should not detect conflict for non-customer resource
        conflicts = _check_resource_locks("ticket:456", "secondary-agent")
        assert len(conflicts) == 0
    
    def test_check_frequency_caps(self):
        """Test frequency cap conflict detection."""
        # Should detect conflict for email actions
        conflicts = _check_frequency_caps("email.send", "test-author")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "frequency_cap"
        
        # Should not detect conflict for non-email actions
        conflicts = _check_frequency_caps("api.call", "test-author")
        assert len(conflicts) == 0
    
    def test_check_idempotency_conflicts(self):
        """Test idempotency conflict detection."""
        # Should detect conflict for keys containing 'duplicate'
        conflicts = _check_idempotency_conflicts("duplicate_key_123", "test_op")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == "idempotency_conflict"
        
        # Should not detect conflict for normal keys
        conflicts = _check_idempotency_conflicts("normal_key_123", "test_op")
        assert len(conflicts) == 0


class TestGhostRunFunction:
    """Test the main ghost_run function."""
    
    @pytest.mark.asyncio
    async def test_ghost_run_basic(self):
        """Test basic ghost_run functionality."""
        # Create a mock graph
        mock_graph = Mock()
        
        # Mock the GhostSimulator to avoid LangGraph API issues
        with patch('meshmind.ghost.simulator.GhostSimulator') as mock_simulator_class:
            mock_simulator = Mock()
            mock_simulator_class.return_value = mock_simulator
            
            # Mock the simulate method
            mock_report = GhostReport(
                simulation_id="test",
                total_steps=1,
                total_cost=0.01,
                total_tokens=100,
                execution_time_ms=50.0,
                llm_calls=1,
                api_calls=0,
                effects_count=0,
                steps=[],
                conflicts=[],
                policy_violations=[],
                budget_exceeded=False,
                input_state={"test": "data"}
            )
            mock_simulator.simulate = AsyncMock(return_value=mock_report)
            
            # Test the function
            result = await ghost_run(
                mock_graph,
                {"test": "data"},
                budget_cap=5.0,
                rpm_limit=30
            )
            
            assert isinstance(result, GhostReport)
            assert result.total_cost == 0.01
            
            # Verify simulator was created with correct config
            mock_simulator_class.assert_called_once()
            config = mock_simulator_class.call_args[0][0]
            assert config.budget_cap == 5.0
            assert config.rpm_limit == 30


class TestConflictReport:
    """Test ConflictReport functionality."""
    
    def test_conflict_report_creation(self):
        """Test creating a conflict report."""
        conflict = ConflictReport(
            conflict_type="resource_lock",
            resource="customer:123",
            node_name="send_email",
            step_number=2,
            severity="high",
            description="Resource is locked by another process",
            suggested_fix="Use resource hold request",
            metadata={"lock_id": "abc123"}
        )
        
        assert conflict.conflict_type == "resource_lock"
        assert conflict.resource == "customer:123"
        assert conflict.node_name == "send_email"
        assert conflict.step_number == 2
        assert conflict.severity == "high"
        assert conflict.description == "Resource is locked by another process"
        assert conflict.suggested_fix == "Use resource hold request"
        assert conflict.metadata["lock_id"] == "abc123"


class TestStepReport:
    """Test StepReport functionality."""
    
    def test_step_report_creation(self):
        """Test creating a step report."""
        conflicts = [
            ConflictReport("test_conflict", "test_resource", "test_node", 0, "low", "Test conflict")
        ]
        
        step = StepReport(
            step_number=1,
            node_name="analyze_ticket",
            duration_ms=150.5,
            cost=0.025,
            tokens=250,
            conflicts=conflicts,
            budget_exceeded=False,
            error=None,
            state_snapshot={"ticket_id": "123"}
        )
        
        assert step.step_number == 1
        assert step.node_name == "analyze_ticket"
        assert step.duration_ms == 150.5
        assert step.cost == 0.025
        assert step.tokens == 250
        assert len(step.conflicts) == 1
        assert step.budget_exceeded is False
        assert step.error is None
        assert step.state_snapshot["ticket_id"] == "123"
    
    def test_step_report_with_error(self):
        """Test creating a step report with an error."""
        step = StepReport(
            step_number=0,
            node_name="error_node",
            duration_ms=0.0,
            cost=0.0,
            tokens=0,
            conflicts=[],
            budget_exceeded=False,
            error="Test error message"
        )
        
        assert step.error == "Test error message"
        assert step.cost == 0.0
        assert step.tokens == 0


if __name__ == "__main__":
    pytest.main([__file__])
