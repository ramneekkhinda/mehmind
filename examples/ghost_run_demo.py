"""
Ghost-Run Demo: Comprehensive example of using MeshMind Ghost-Run.

This demo shows how to:
1. Create a LangGraph workflow with MeshMind safety controls
2. Run Ghost-Run simulation to predict costs and conflicts
3. Compare different workflow configurations
4. Generate detailed reports
"""

import asyncio
import json
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from meshmind import wrap_node, BudgetContext, call_model, http_post, email_send
from meshmind.ghost import ghost_run, GhostConfig


# Define workflow nodes with MeshMind protection
@wrap_node(lambda s: ("ticket.analyze", {
    "resource": f"ticket:{s['ticket_id']}",
    "author": "support-agent"
}))
async def analyze_ticket(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze support ticket with budget control."""
    
    async with BudgetContext(usd_cap=1.0, rpm=30) as budget:
        analysis = await call_model(
            f"Analyze this support ticket: {state['description']}",
            budget,
            provider="sim"
        )
    
    return {
        "analysis": analysis,
        "priority": "high" if "urgent" in state['description'].lower() else "normal"
    }


@wrap_node(lambda s: ("response.generate", {
    "resource": f"ticket:{s['ticket_id']}",
    "author": "support-agent"
}))
async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate response to customer."""
    
    async with BudgetContext(usd_cap=1.5, rpm=30) as budget:
        response = await call_model(
            f"Generate a helpful response for: {state['description']}",
            budget,
            provider="sim"
        )
    
    return {"response": response}


@wrap_node(lambda s: ("email.send", {
    "resource": f"customer:{s['customer_email']}",
    "author": "support-agent"
}))
async def send_email(state: Dict[str, Any]) -> Dict[str, Any]:
    """Send email to customer."""
    
    try:
        result = await email_send(
            contact_id=state['customer_id'],
            body=state['response'],
            subject=f"Re: {state['subject']}",
            idempotency_key=f"response:{state['ticket_id']}"
        )
        return {"email_sent": True, "email_id": result.get("message_id")}
    except Exception as e:
        return {"email_sent": False, "error": str(e)}


@wrap_node(lambda s: ("crm.update", {
    "resource": f"ticket:{s['ticket_id']}",
    "author": "support-agent"
}))
async def update_crm(state: Dict[str, Any]) -> Dict[str, Any]:
    """Update CRM system."""
    
    try:
        result = await http_post(
            url="https://api.crm.com/tickets/update",
            data={
                "ticket_id": state['ticket_id'],
                "status": "responded",
                "response": state['response']
            },
            idempotency_key=f"crm_update:{state['ticket_id']}"
        )
        return {"crm_updated": True, "crm_id": result.get("id")}
    except Exception as e:
        return {"crm_updated": False, "error": str(e)}


# Create the workflow
def create_support_workflow() -> StateGraph:
    """Create the support ticket workflow."""
    
    # Create a simple workflow for demo purposes
    from typing import TypedDict
    
    class WorkflowState(TypedDict):
        ticket_id: str
        customer_id: str
        customer_email: str
        subject: str
        description: str
        analysis: str
        response: str
        email_sent: bool
        crm_updated: bool
    
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_ticket)
    workflow.add_node("generate", generate_response)
    workflow.add_node("email", send_email)
    workflow.add_node("crm", update_crm)
    
    # Define edges
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "generate")
    workflow.add_edge("generate", "email")
    workflow.add_edge("email", "crm")
    workflow.add_edge("crm", END)
    
    return workflow


async def demo_ghost_run():
    """Demonstrate Ghost-Run functionality."""
    
    print("🧾 MESHMIND GHOST-RUN DEMO")
    print("=" * 50)
    
    # Create workflow
    workflow = create_support_workflow()
    
    # Test input state
    input_state = {
        "ticket_id": "TICKET-123",
        "customer_id": "CUST-456",
        "customer_email": "customer@example.com",
        "subject": "Product not working",
        "description": "I purchased your product last week and it's not working properly. This is urgent as I need it for an important meeting tomorrow."
    }
    
    print(f"\n📋 Input State:")
    print(json.dumps(input_state, indent=2))
    
    # Run Ghost-Run simulation
    print(f"\n🔮 Running Ghost-Run simulation...")
    
    config = GhostConfig(
        budget_cap=5.0,
        rpm_limit=60,
        fail_on_conflict=False,
        max_steps=10
    )
    
    report = await ghost_run(workflow, input_state, budget_cap=config.budget_cap, rpm_limit=config.rpm_limit, fail_on_conflict=config.fail_on_conflict, max_steps=config.max_steps)
    
    # Display results
    print(f"\n📊 SIMULATION RESULTS:")
    print(f"  Status: {'✅ PASSED' if not report.budget_exceeded and len(report.conflicts) == 0 else '⚠️  WARNINGS' if len(report.conflicts) <= 2 else '❌ FAILED'}")
    print(f"  Total Cost: ${report.total_cost:.3f}")
    print(f"  Total Tokens: {report.total_tokens:,}")
    print(f"  Execution Time: {report.execution_time_ms:.0f}ms")
    print(f"  LLM Calls: {report.llm_calls}")
    print(f"  API Calls: {report.api_calls}")
    print(f"  Side Effects: {report.effects_count}")
    print(f"  Conflicts: {len(report.conflicts)}")
    print(f"  Policy Violations: {len(report.policy_violations)}")
    
    # Cost breakdown
    if report.total_cost > 0:
        print(f"\n💰 COST BREAKDOWN:")
        cost_breakdown = report.get_cost_breakdown()
        for node, cost in cost_breakdown.items():
            print(f"  {node}: ${cost:.3f}")
    
    # Conflicts
    if report.conflicts:
        print(f"\n🚨 CONFLICTS DETECTED:")
        for i, conflict in enumerate(report.conflicts, 1):
            print(f"  {i}. {conflict.conflict_type} - {conflict.description}")
            if conflict.suggested_fix:
                print(f"     💡 Fix: {conflict.suggested_fix}")
    
    # Policy violations
    if report.policy_violations:
        print(f"\n📋 POLICY VIOLATIONS:")
        for violation in report.policy_violations:
            print(f"  - {violation}")
    
    # Save reports
    timestamp = report.timestamp.replace(':', '-').split('.')[0]
    
    # Save JSON report
    json_path = f"ghost_run_demo_{timestamp}.json"
    with open(json_path, 'w') as f:
        f.write(report.to_json())
    print(f"\n📄 JSON report saved to: {json_path}")
    
    # Save HTML report
    from meshmind.ghost.reports import save_html_report
    html_path = f"ghost_run_demo_{timestamp}.html"
    save_html_report(report, html_path, "Support Ticket Workflow - Ghost-Run Report")
    print(f"📄 HTML report saved to: {html_path}")
    
    return report


async def demo_comparison():
    """Demonstrate comparing different workflow configurations."""
    
    print(f"\n🔄 COMPARISON DEMO")
    print("=" * 50)
    
    workflow = create_support_workflow()
    input_state = {
        "ticket_id": "TICKET-456",
        "customer_id": "CUST-789",
        "customer_email": "customer2@example.com",
        "subject": "General inquiry",
        "description": "I have a question about your pricing plans."
    }
    
    # Test different budget caps
    budgets = [1.0, 2.0, 5.0, 10.0]
    results = []
    
    for budget in budgets:
        print(f"\n💰 Testing with ${budget} budget cap...")
        
        config = GhostConfig(
            budget_cap=budget,
            rpm_limit=60,
            fail_on_conflict=False
        )
        
        report = await ghost_run(workflow, input_state, budget_cap=config.budget_cap, rpm_limit=config.rpm_limit, fail_on_conflict=config.fail_on_conflict)
        results.append({
            "budget_cap": budget,
            "total_cost": report.total_cost,
            "budget_exceeded": report.budget_exceeded,
            "conflicts": len(report.conflicts),
            "success": not report.budget_exceeded and len(report.conflicts) == 0
        })
        
        status = "✅ PASS" if results[-1]["success"] else "❌ FAIL"
        print(f"  {status} - Cost: ${report.total_cost:.3f}, Conflicts: {len(report.conflicts)}")
    
    # Summary
    print(f"\n📊 COMPARISON SUMMARY:")
    print(f"{'Budget':<8} {'Cost':<8} {'Exceeded':<10} {'Conflicts':<10} {'Status':<8}")
    print("-" * 50)
    for result in results:
        status = "PASS" if result["success"] else "FAIL"
        exceeded = "Yes" if result["budget_exceeded"] else "No"
        print(f"${result['budget_cap']:<7} ${result['total_cost']:<7.3f} {exceeded:<10} {result['conflicts']:<10} {status:<8}")


async def main():
    """Main demo function."""
    
    # Run basic Ghost-Run demo
    await demo_ghost_run()
    
    # Run comparison demo
    await demo_comparison()
    
    print(f"\n🎉 Ghost-Run demo completed!")
    print(f"Check the generated HTML report for detailed analysis.")


if __name__ == "__main__":
    asyncio.run(main())
