"""
RAG Evaluation using RAGAS framework
Evaluates the multi-agent RAG system with standard RAG metrics.

Usage:
    python scripts/eval_rag_ragas.py --test-file data/eval/test_cases.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_ragas_installed() -> bool:
    """Check if RAGAS is installed."""
    try:
        import ragas
        return True
    except ImportError:
        return False


def run_ragas_evaluation(test_cases_path: str) -> dict[str, Any]:
    """
    Run RAGAS evaluation on test cases.

    Args:
        test_cases_path: Path to JSON file with test cases

    Returns:
        Dictionary with evaluation results
    """
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
        )
        from datasets import Dataset
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("\nInstall RAGAS:")
        print("  pip install ragas datasets")
        sys.exit(1)

    # Load test cases
    test_path = Path(test_cases_path)
    if not test_path.exists():
        print(f"❌ Test cases file not found: {test_cases_path}")
        print("\nExpected format:")
        print("""
{
  "test_cases": [
    {
      "question": "What is the capital of France?",
      "answer": "The capital of France is Paris.",
      "contexts": ["Paris is the capital and most populous city of France."],
      "ground_truth": "Paris"
    }
  ]
}
        """)
        sys.exit(1)

    with open(test_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get('test_cases', [])
    if not test_cases:
        print("❌ No test cases found in file")
        sys.exit(1)

    print(f"📊 Loaded {len(test_cases)} test cases")

    # Prepare dataset
    dataset_dict = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    for tc in test_cases:
        dataset_dict["question"].append(tc["question"])
        dataset_dict["answer"].append(tc["answer"])
        dataset_dict["contexts"].append(tc["contexts"])
        dataset_dict["ground_truth"].append(tc.get("ground_truth", ""))

    dataset = Dataset.from_dict(dataset_dict)

    # Run evaluation
    print("\n🔍 Running RAGAS evaluation...")
    print("Metrics: faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness")

    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
        ],
    )

    return result


def run_simple_evaluation(test_cases_path: str) -> dict[str, Any]:
    """
    Run simple evaluation without RAGAS.
    Basic accuracy and relevance checks.

    Args:
        test_cases_path: Path to JSON file with test cases

    Returns:
        Dictionary with evaluation results
    """
    from app.graph.streaming_helpers import run_query_workflow
    from app.core.settings import get_settings

    settings = get_settings()

    # Load test cases
    test_path = Path(test_cases_path)
    if not test_path.exists():
        print(f"❌ Test cases file not found: {test_cases_path}")
        sys.exit(1)

    with open(test_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get('test_cases', [])
    print(f"📊 Loaded {len(test_cases)} test cases")

    results = []
    total_score = 0.0

    for i, tc in enumerate(test_cases, 1):
        question = tc["question"]
        ground_truth = tc.get("ground_truth", "")

        print(f"\n[{i}/{len(test_cases)}] Evaluating: {question[:50]}...")

        try:
            # Run query through the RAG system
            result = run_query_workflow(
                query=question,
                session_id=f"eval_{i}",
                user_id="evaluator",
                stream=False
            )

            answer = result.get("answer", "")

            # Simple relevance check (keyword matching)
            if ground_truth:
                # Normalize for comparison
                answer_lower = answer.lower()
                truth_lower = ground_truth.lower()

                # Check if key terms from ground truth appear in answer
                truth_words = set(truth_lower.split())
                answer_words = set(answer_lower.split())

                overlap = len(truth_words & answer_words)
                relevance_score = overlap / len(truth_words) if truth_words else 0.0
            else:
                # If no ground truth, just check if we got an answer
                relevance_score = 1.0 if answer.strip() else 0.0

            total_score += relevance_score

            results.append({
                "question": question,
                "answer": answer[:200],  # Truncate for display
                "relevance_score": relevance_score,
                "status": "✅" if relevance_score > 0.5 else "⚠️"
            })

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "question": question,
                "answer": "",
                "relevance_score": 0.0,
                "status": "❌",
                "error": str(e)
            })

    avg_score = total_score / len(test_cases) if test_cases else 0.0

    return {
        "total_cases": len(test_cases),
        "average_relevance": avg_score,
        "results": results
    }


def print_results(result: dict[str, Any], use_ragas: bool) -> None:
    """Print evaluation results."""
    print("\n" + "=" * 80)
    print("📈 EVALUATION RESULTS")
    print("=" * 80)

    if use_ragas:
        print("\nRAGAS Metrics:")
        for key, value in result.items():
            if isinstance(value, (int, float)):
                print(f"  {key:25s}: {value:.4f}")
    else:
        print(f"\nTotal test cases: {result['total_cases']}")
        print(f"Average relevance: {result['average_relevance']:.4f}")

        print("\nDetailed results:")
        for i, res in enumerate(result['results'], 1):
            print(f"\n[{i}] {res['status']} {res['question'][:60]}...")
            print(f"    Score: {res['relevance_score']:.2f}")
            if res.get('error'):
                print(f"    Error: {res['error']}")

    print("\n" + "=" * 80)


def create_example_test_file(output_path: str) -> None:
    """Create an example test cases file."""
    example_data = {
        "test_cases": [
            {
                "question": "什么是RAG？",
                "answer": "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的技术。",
                "contexts": [
                    "RAG是检索增强生成技术，通过检索相关文档来增强LLM的回答质量。"
                ],
                "ground_truth": "RAG是检索增强生成技术"
            },
            {
                "question": "What are the benefits of vector search?",
                "answer": "Vector search enables semantic similarity matching.",
                "contexts": [
                    "Vector search uses embeddings to find semantically similar content."
                ],
                "ground_truth": "Semantic similarity matching"
            }
        ]
    }

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path_obj, 'w', encoding='utf-8') as f:
        json.dump(example_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Created example test file: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation with RAGAS")
    parser.add_argument(
        "--test-file",
        type=str,
        default="data/eval/test_cases.json",
        help="Path to test cases JSON file"
    )
    parser.add_argument(
        "--create-example",
        action="store_true",
        help="Create an example test file and exit"
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Use simple evaluation (no RAGAS dependency)"
    )

    args = parser.parse_args()

    if args.create_example:
        create_example_test_file(args.test_file)
        return

    # Check if RAGAS is available
    has_ragas = check_ragas_installed()
    use_ragas = has_ragas and not args.simple

    if not use_ragas and not args.simple:
        print("⚠️  RAGAS not installed. Using simple evaluation.")
        print("   Install RAGAS for advanced metrics: pip install ragas datasets")
        print()

    # Run evaluation
    if use_ragas:
        result = run_ragas_evaluation(args.test_file)
    else:
        result = run_simple_evaluation(args.test_file)

    # Print results
    print_results(result, use_ragas)


if __name__ == "__main__":
    main()
