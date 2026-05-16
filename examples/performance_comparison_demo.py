"""
Demo script for the performance comparison framework.

This demonstrates how to use the evaluation module to compare
different retrieval strategies.
"""

from app.evaluation import (
    TestQuery,
    EvaluationService,
    load_test_queries,
    calculate_all_metrics,
)


def demo_metrics():
    """Demonstrate evaluation metrics calculation."""
    print("=" * 80)
    print("EVALUATION METRICS DEMO")
    print("=" * 80)
    
    # Example retrieval results
    retrieved = ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']
    relevant = {'doc1', 'doc3', 'doc5'}
    
    metrics = calculate_all_metrics(retrieved, relevant, k=5)
    
    print(f"\nRetrieved documents: {retrieved}")
    print(f"Relevant documents: {relevant}")
    print(f"\nMetrics:")
    print(f"  Precision@5: {metrics['precision']:.3f}")
    print(f"  Recall@5: {metrics['recall']:.3f}")
    print(f"  F1@5: {metrics['f1']:.3f}")
    print(f"  Reciprocal Rank: {metrics['reciprocal_rank']:.3f}")
    print(f"  NDCG@5: {metrics['ndcg']:.3f}")


def demo_test_queries():
    """Demonstrate loading test queries."""
    print("\n" + "=" * 80)
    print("TEST QUERIES DEMO")
    print("=" * 80)
    
    queries = load_test_queries('data/evaluation/demo_queries.json')
    
    print(f"\nLoaded {len(queries)} test queries")
    print(f"Categories: {', '.join(sorted(set(q.category for q in queries)))}")
    print(f"Difficulties: {', '.join(sorted(set(q.difficulty for q in queries)))}")
    
    print("\nSample queries:")
    for i, query in enumerate(queries[:3], 1):
        print(f"\n{i}. [{query.category}] {query.query}")
        print(f"   Expected docs: {', '.join(query.expected_docs)}")
        print(f"   Difficulty: {query.difficulty}")


def demo_baseline_usage():
    """Demonstrate how to use baseline retrievers."""
    print("\n" + "=" * 80)
    print("BASELINE RETRIEVER USAGE")
    print("=" * 80)
    
    print("""
To use the baseline retrievers, you need to:

1. Vector-only baseline:
   from app.baselines import create_vector_baseline
   
   baseline = create_vector_baseline(
       vectorstore=your_chroma_instance,
       k=5,
       score_threshold=0.5
   )
   result = baseline.retrieve("your query", "query_id")

2. Hybrid baseline (vector + BM25):
   from app.baselines import create_hybrid_baseline
   
   baseline = create_hybrid_baseline(
       vectorstore=your_chroma_instance,
       bm25_index=your_bm25_index,
       doc_id_map=your_doc_id_mapping,
       k=5,
       alpha=0.5  # 0.5 = equal weight for vector and BM25
   )
   result = baseline.retrieve("your query", "query_id")

3. Rerank baseline:
   from app.baselines import create_rerank_baseline
   
   def rerank_function(query, docs):
       # Your reranking logic here
       # Return list of scores for each doc
       return [0.9, 0.8, 0.7, ...]
   
   baseline = create_rerank_baseline(
       vectorstore=your_chroma_instance,
       rerank_fn=rerank_function,
       k=5,
       initial_k=20  # Retrieve 20, rerank to top 5
   )
   result = baseline.retrieve("your query", "query_id")

4. Run evaluation:
   from app.evaluation import EvaluationService
   
   service = EvaluationService(k=5)
   eval_run = service.evaluate_system(
       system=baseline,
       test_queries=queries,
       system_name="vector_only"
   )
   
   print(f"Precision@5: {eval_run.metrics.precision_at_5:.3f}")
   print(f"Recall@5: {eval_run.metrics.recall_at_5:.3f}")
   print(f"F1@5: {eval_run.metrics.f1_at_5:.3f}")

5. Compare multiple systems:
   systems = {
       "vector_only": vector_baseline,
       "hybrid": hybrid_baseline,
       "rerank": rerank_baseline
   }
   
   comparisons = service.compare_systems(systems, test_queries)
   service.print_comparison(comparisons)
""")


if __name__ == "__main__":
    demo_metrics()
    demo_test_queries()
    demo_baseline_usage()
    
    print("\n" + "=" * 80)
    print("For full integration, connect the baselines to your Chroma vectorstore")
    print("and implement the reranking function using a cross-encoder model.")
    print("=" * 80 + "\n")
