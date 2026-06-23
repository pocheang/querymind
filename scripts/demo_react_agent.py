"""
ReAct Agent Demo Script

This script demonstrates the ReAct (Reasoning + Acting) agent functionality.
Run with: python scripts/demo_react_agent.py
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.react_agent import run_react_agent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def demo_simple_query():
    """Demo: Simple query that ReAct can handle."""
    print("\n" + "=" * 80)
    print("Demo 1: Simple Information Query")
    print("=" * 80)

    question = "什么是APT28？它的主要攻击手法是什么？"
    print(f"\n问题: {question}\n")

    try:
        result = run_react_agent(
            question=question,
            use_reasoning=False,
            max_iterations=3,
        )

        print(f"答案:\n{result['answer']}\n")
        print(f"使用迭代次数: {result['iterations_used']}")

        print("\nReAct思考过程:")
        for step in result.get("react_history", []):
            print(f"\n第{step['iteration']}轮:")
            print(f"  思考: {step['thought']['thought']}")
            print(f"  行动: {step['thought']['action']}({step['thought']['action_input']})")
            if step.get("observation"):
                print(f"  观察: {step['observation']['result']}")

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)


def demo_comparison_query():
    """Demo: Comparison query requiring multiple searches."""
    print("\n" + "=" * 80)
    print("Demo 2: Comparison Query (Multi-step)")
    print("=" * 80)

    question = "比较APT28和APT29的攻击手法，找出它们的共同点和差异"
    print(f"\n问题: {question}\n")

    try:
        result = run_react_agent(
            question=question,
            use_reasoning=True,  # Enable reasoning for complex query
            max_iterations=5,
        )

        print(f"答案:\n{result['answer']}\n")
        print(f"使用迭代次数: {result['iterations_used']}")

        print("\nReAct思考过程:")
        for step in result.get("react_history", []):
            print(f"\n第{step['iteration']}轮:")
            print(f"  思考: {step['thought']['thought']}")
            print(f"  行动: {step['thought']['action']}({step['thought']['action_input']})")
            print(f"  推理: {step['thought']['reasoning']}")
            if step.get("observation"):
                print(f"  观察: {step['observation']['result']}")

        # Show accumulated contexts
        contexts = result.get("contexts", {})
        print("\n累积的上下文:")
        for ctx_type, ctx_content in contexts.items():
            if ctx_content:
                print(f"  {ctx_type}: {len(ctx_content)} 字符")

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)


def demo_investigative_query():
    """Demo: Investigative query using multiple tools."""
    print("\n" + "=" * 80)
    print("Demo 3: Investigative Query (Multi-tool)")
    print("=" * 80)

    question = "调查公司的财务报销政策，检查是否有预算限制，并查找相关的审批流程"
    print(f"\n问题: {question}\n")

    try:
        result = run_react_agent(
            question=question,
            use_reasoning=True,
            max_iterations=5,
        )

        print(f"答案:\n{result['answer']}\n")
        print(f"使用迭代次数: {result['iterations_used']}")

        print("\n工具使用统计:")
        tool_usage = {}
        for step in result.get("react_history", []):
            action = step['thought']['action']
            tool_usage[action] = tool_usage.get(action, 0) + 1

        for tool, count in tool_usage.items():
            print(f"  {tool}: {count}次")

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "ReAct Agent Demonstration" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")

    demos = [
        ("Simple Query", demo_simple_query),
        ("Comparison Query", demo_comparison_query),
        ("Investigative Query", demo_investigative_query),
    ]

    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Run all demos")

    try:
        choice = input("\nSelect demo (0-3): ").strip()

        if choice == "0":
            for name, demo_func in demos:
                demo_func()
        elif choice in ["1", "2", "3"]:
            idx = int(choice) - 1
            demos[idx][1]()
        else:
            print("Invalid choice. Running all demos...")
            for name, demo_func in demos:
                demo_func()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        logger.error(f"Error running demo: {e}", exc_info=True)

    print("\n" + "=" * 80)
    print("Demo completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
