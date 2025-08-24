"""
Tests for Ghost-Run reporting functionality.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from meshmind.ghost.reports import (
    GhostReport, 
    StepReport, 
    ConflictReport,
    generate_html_report,
    save_html_report,
    save_json_report
)


class TestHTMLReportGeneration:
    """Test HTML report generation."""
    
    @pytest.mark.unit
    def test_generate_html_report_basic(self):
        """Test basic HTML report generation."""
        # Create a simple report
        steps = [
            StepReport(0, "node1", 50.0, 0.01, 100, []),
            StepReport(1, "node2", 75.0, 0.02, 200, [])
        ]
        
        report = GhostReport(
            simulation_id="test_html",
            total_steps=2,
            total_cost=0.03,
            total_tokens=300,
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
        
        html = generate_html_report(report, "Test Report")
        
        # Check that HTML contains expected elements
        assert "<!DOCTYPE html>" in html
        assert "Test Report" in html
        assert "test_html" in html
        assert "$0.03" in html
        assert "300" in html  # tokens
        assert "125" in html  # execution time (without ms suffix in summary)
        assert "node1" in html
        assert "node2" in html
    
    @pytest.mark.unit
    def test_generate_html_report_with_conflicts(self):
        """Test HTML report generation with conflicts."""
        conflicts = [
            ConflictReport(
                "resource_lock", 
                "customer:123", 
                "send_email", 
                1, 
                "high", 
                "Resource locked",
                "Use hold request"
            ),
            ConflictReport(
                "frequency_cap", 
                "email:limit", 
                "send_email", 
                1, 
                "medium", 
                "Frequency exceeded"
            )
        ]
        
        steps = [
            StepReport(0, "analyze", 50.0, 0.01, 100, []),
            StepReport(1, "send_email", 75.0, 0.02, 200, conflicts)
        ]
        
        report = GhostReport(
            simulation_id="test_conflicts",
            total_steps=2,
            total_cost=0.03,
            total_tokens=300,
            execution_time_ms=125.0,
            llm_calls=2,
            api_calls=0,
            effects_count=0,
            steps=steps,
            conflicts=conflicts,
            policy_violations=[],
            budget_exceeded=False,
            input_state={"test": "data"}
        )
        
        html = generate_html_report(report)
        
        # Check conflict-related content
        assert "Resource Lock" in html
        assert "Frequency Cap" in html
        assert "Resource locked" in html
        assert "Use hold request" in html
        assert "HIGH" in html
        assert "MEDIUM" in html
    
    @pytest.mark.unit
    def test_generate_html_report_budget_exceeded(self):
        """Test HTML report generation with budget exceeded."""
        report = GhostReport(
            simulation_id="test_budget",
            total_steps=1,
            total_cost=15.0,  # High cost
            total_tokens=1000,
            execution_time_ms=100.0,
            llm_calls=1,
            api_calls=0,
            effects_count=0,
            steps=[],
            conflicts=[],
            policy_violations=[],
            budget_exceeded=True,
            input_state={}
        )
        
        html = generate_html_report(report)
        
        # Should show failed status and budget exceeded
        assert "Budget Exceeded:</strong> Yes" in html
    
    @pytest.mark.unit
    def test_generate_html_report_with_policy_violations(self):
        """Test HTML report generation with policy violations."""
        report = GhostReport(
            simulation_id="test_policy",
            total_steps=1,
            total_cost=0.01,
            total_tokens=100,
            execution_time_ms=50.0,
            llm_calls=1,
            api_calls=0,
            effects_count=0,
            steps=[],
            conflicts=[],
            policy_violations=["Email frequency exceeded", "Budget cap violation"],
            budget_exceeded=False,
            input_state={}
        )
        
        html = generate_html_report(report)
        
        # Check policy violations
        assert "Email frequency exceeded" in html
        assert "Budget cap violation" in html


class TestReportSaving:
    """Test report saving functionality."""
    
    @pytest.mark.integration
    def test_save_html_report(self):
        """Test saving HTML report to file."""
        report = GhostReport(
            simulation_id="test_save",
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            temp_path = f.name
        
        try:
            save_html_report(report, temp_path, "Test Save Report")
            
            # Check file was created and contains expected content
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Test Save Report" in content
                assert "test_save" in content
                assert "$0.01" in content
        
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.integration
    def test_save_json_report(self):
        """Test saving JSON report to file."""
        report = GhostReport(
            simulation_id="test_json_save",
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            save_json_report(report, temp_path)
            
            # Check file was created and contains valid JSON
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert data["simulation_id"] == "test_json_save"
                assert data["total_cost"] == 0.01
                assert data["input_state"]["test"] == "data"
        
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestReportDataStructures:
    """Test report data structure functionality."""
    
    @pytest.mark.unit
    def test_conflict_report_serialization(self):
        """Test ConflictReport serialization."""
        conflict = ConflictReport(
            conflict_type="test_type",
            resource="test_resource",
            node_name="test_node",
            step_number=1,
            severity="high",
            description="Test description",
            suggested_fix="Test fix",
            metadata={"key": "value"}
        )
        
        # Should be serializable to dict
        conflict_dict = conflict.__dict__
        assert conflict_dict["conflict_type"] == "test_type"
        assert conflict_dict["metadata"]["key"] == "value"
    
    @pytest.mark.unit
    def test_step_report_serialization(self):
        """Test StepReport serialization."""
        conflicts = [
            ConflictReport("test", "res", "node", 0, "low", "desc")
        ]
        
        step = StepReport(
            step_number=1,
            node_name="test_node",
            duration_ms=100.0,
            cost=0.01,
            tokens=50,
            conflicts=conflicts,
            budget_exceeded=False,
            error=None,
            state_snapshot={"key": "value"}
        )
        
        # Should be serializable
        step_dict = step.__dict__
        assert step_dict["step_number"] == 1
        assert step_dict["node_name"] == "test_node"
        assert len(step_dict["conflicts"]) == 1
        assert step_dict["state_snapshot"]["key"] == "value"
    
    @pytest.mark.unit
    def test_ghost_report_complete_serialization(self):
        """Test complete GhostReport serialization."""
        conflicts = [
            ConflictReport("resource_lock", "res1", "node1", 0, "high", "Lock conflict")
        ]
        
        steps = [
            StepReport(0, "node1", 50.0, 0.01, 100, conflicts),
            StepReport(1, "node2", 75.0, 0.02, 200, [])
        ]
        
        report = GhostReport(
            simulation_id="test_complete",
            total_steps=2,
            total_cost=0.03,
            total_tokens=300,
            execution_time_ms=125.0,
            llm_calls=2,
            api_calls=1,
            effects_count=1,
            steps=steps,
            conflicts=conflicts,
            policy_violations=["Test violation"],
            budget_exceeded=False,
            input_state={"input": "test"}
        )
        
        # Test to_dict method
        report_dict = report.to_dict()
        assert report_dict["simulation_id"] == "test_complete"
        assert report_dict["total_cost"] == 0.03
        assert len(report_dict["steps"]) == 2
        assert len(report_dict["conflicts"]) == 1
        assert len(report_dict["policy_violations"]) == 1
        
        # Test to_json method
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["simulation_id"] == "test_complete"
        assert parsed["total_cost"] == 0.03


class TestReportAnalytics:
    """Test report analytics functionality."""
    
    @pytest.mark.unit
    def test_cost_breakdown_complex(self):
        """Test cost breakdown with multiple nodes."""
        steps = [
            StepReport(0, "analyze", 50.0, 0.01, 100, []),
            StepReport(1, "generate", 75.0, 0.02, 200, []),
            StepReport(2, "analyze", 25.0, 0.005, 50, []),  # Same node again
            StepReport(3, "send", 100.0, 0.001, 10, []),
            StepReport(4, "generate", 60.0, 0.015, 150, [])  # Same node again
        ]
        
        report = GhostReport(
            simulation_id="test_breakdown",
            total_steps=5,
            total_cost=0.051,
            total_tokens=510,
            execution_time_ms=310.0,
            llm_calls=4,
            api_calls=1,
            effects_count=0,
            steps=steps,
            conflicts=[],
            policy_violations=[],
            budget_exceeded=False,
            input_state={}
        )
        
        breakdown = report.get_cost_breakdown()
        
        # Check aggregated costs
        assert breakdown["analyze"] == 0.015  # 0.01 + 0.005
        assert breakdown["generate"] == 0.035  # 0.02 + 0.015
        assert breakdown["send"] == 0.001
        assert len(breakdown) == 3
    
    @pytest.mark.unit
    def test_conflicts_by_type_complex(self):
        """Test grouping conflicts by type with multiple types."""
        conflicts = [
            ConflictReport("resource_lock", "res1", "node1", 0, "high", "Lock 1"),
            ConflictReport("frequency_cap", "res2", "node2", 1, "medium", "Freq 1"),
            ConflictReport("resource_lock", "res3", "node3", 2, "low", "Lock 2"),
            ConflictReport("idempotency_conflict", "res4", "node4", 3, "high", "Idem 1"),
            ConflictReport("frequency_cap", "res5", "node5", 4, "medium", "Freq 2"),
            ConflictReport("resource_lock", "res6", "node6", 5, "critical", "Lock 3")
        ]
        
        report = GhostReport(
            simulation_id="test_conflicts_grouped",
            total_steps=6,
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
        
        assert len(grouped["resource_lock"]) == 3
        assert len(grouped["frequency_cap"]) == 2
        assert len(grouped["idempotency_conflict"]) == 1
        assert len(grouped) == 3
        
        # Check specific conflicts
        resource_locks = grouped["resource_lock"]
        assert any(c.description == "Lock 1" for c in resource_locks)
        assert any(c.description == "Lock 2" for c in resource_locks)
        assert any(c.description == "Lock 3" for c in resource_locks)
    
    @pytest.mark.unit
    def test_summary_with_various_states(self):
        """Test summary generation with various report states."""
        # Test successful report
        success_report = GhostReport(
            simulation_id="success",
            total_steps=2,
            total_cost=0.01,
            total_tokens=100,
            execution_time_ms=50.0,
            llm_calls=1,
            api_calls=1,
            effects_count=0,
            steps=[],
            conflicts=[],
            policy_violations=[],
            budget_exceeded=False,
            input_state={}
        )
        
        summary = success_report.get_summary()
        assert summary["success"] is True
        assert summary["conflicts_count"] == 0
        assert summary["policy_violations_count"] == 0
        
        # Test report with conflicts but no budget exceeded
        conflict_report = GhostReport(
            simulation_id="conflicts",
            total_steps=2,
            total_cost=0.01,
            total_tokens=100,
            execution_time_ms=50.0,
            llm_calls=1,
            api_calls=1,
            effects_count=0,
            steps=[],
            conflicts=[ConflictReport("test", "res", "node", 0, "low", "desc")],
            policy_violations=[],
            budget_exceeded=False,
            input_state={}
        )
        
        summary = conflict_report.get_summary()
        assert summary["success"] is False  # Has conflicts
        assert summary["conflicts_count"] == 1
        
        # Test report with budget exceeded
        budget_report = GhostReport(
            simulation_id="budget_exceeded",
            total_steps=1,
            total_cost=15.0,
            total_tokens=1000,
            execution_time_ms=100.0,
            llm_calls=1,
            api_calls=0,
            effects_count=0,
            steps=[],
            conflicts=[],
            policy_violations=[],
            budget_exceeded=True,
            input_state={}
        )
        
        summary = budget_report.get_summary()
        assert summary["success"] is False  # Budget exceeded
        assert summary["budget_exceeded"] is True


if __name__ == "__main__":
    pytest.main([__file__])
