"""
Phase 1 Master Verification Script
==================================
Tests all 4 foundation services end-to-end:
1. KnowledgeGraph (DAG Traversal & NetworkX Ancestors)
2. MLEngine (2-PL IRT, BKT Mastery, & Struggle Risk)
3. CareerBenchmarkService (Role Readiness % & Critical Gaps)
4. RAGService (Direct Concept Lookup & Live Pinecone Vector Search)
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
# Add project root and server to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from server.services.knowledge_graph import knowledge_graph
from server.services.ml_engine import ml_engine
from server.services.career_benchmarks import career_benchmarks
from server.services.rag_service import rag_service


def test_knowledge_graph():
    print("\n" + "=" * 50)
    print(" 1. TESTING KNOWLEDGE GRAPH (DAG Traversal)")
    print("=" * 50)

    # Test 1A: Concept Retrieval
    concept = knowledge_graph.get_concept("sql_joins")
    assert concept is not None, "FAILED: 'sql_joins' concept not found in graph."
    print(f"✓ Retrieved Concept: {concept.name} (Depth: {concept.depth_level})")

    # Test 1B: Traverse Up (Correct Answer)
    next_up = knowledge_graph.traverse_up("sql_basics")
    print(f"✓ Correct Answer on 'sql_basics' -> Traversed UP to: {next_up}")

    # Test 1C: Traverse Down (Incorrect Answer)
    next_down = knowledge_graph.traverse_down("sql_joins")
    print(f"✓ Incorrect Answer on 'sql_joins' -> Traversed DOWN to: {next_down}")

    # Test 1D: Root Cause Prerequisite Traversal
    root_causes = knowledge_graph.get_root_causes("sql_window_functions")
    print(f"✓ Root-cause prerequisites for 'sql_window_functions': {root_causes}")
    assert len(root_causes) > 0, "FAILED: Root causes list is empty."


def test_ml_engine():
    print("\n" + "=" * 50)
    print(" 2. TESTING ML ENGINE (2-PL IRT & BKT Math)")
    print("=" * 50)

    # Test 2A: Profile Initialization
    profile = ml_engine.initialize_profile(perceived_level="intermediate")
    print(f"✓ Initialized Profile -> Initial Theta: {profile.theta}, SE: {profile.theta_standard_error}")

    # Test 2B: Record Correct Response
    res1 = ml_engine.record_interaction(
        profile=profile,
        concept_id="sql_basics",
        is_correct=True,
        difficulty=0.35,
        discrimination=1.0,
        response_time_sec=18.0
    )
    print(f"✓ Correct Response -> Updated Theta: {res1['theta']}, BKT Mastery: {res1['concept_mastery']}, Next Action: {res1['next_action']}")

    # Test 2C: Record Incorrect Response with Struggle
    res2 = ml_engine.record_interaction(
        profile=profile,
        concept_id="sql_joins",
        is_correct=False,
        difficulty=0.55,
        discrimination=1.2,
        response_time_sec=95.0  # Latency anomaly (>90s)
    )
    print(f"✓ Incorrect Response (95s latency) -> Updated Theta: {res2['theta']}, BKT Mastery: {res2['concept_mastery']}, Struggle Risk: {res2['struggle_risk']}, Next Action: {res2['next_action']}")


def test_career_benchmarks():
    print("\n" + "=" * 50)
    print(" 3. TESTING CAREER BENCHMARKS (Readiness & Gaps)")
    print("=" * 50)

    # Simulated student scores
    student_scores = {
        "SQL": 0.45,
        "Python": 0.82,
        "Data Visualization": 0.35,
        "Statistics": 0.61
    }

    # Test 3A: Calculate Career Readiness
    readiness = career_benchmarks.calculate_readiness(student_scores, role_identifier="Data Analyst")
    print(f"✓ Data Analyst Readiness Score: {readiness['readiness_percentage']}% (Is Ready: {readiness['is_ready']})")

    # Test 3B: Identify Skill Gaps
    gaps = career_benchmarks.identify_gaps(student_scores, role_identifier="Data Analyst")
    print("✓ Identified Skill Gaps:")
    for gap in gaps:
        print(f"   - Domain: {gap['domain']} | Current: {gap['student_score']} vs Target: {gap['required_benchmark']} | Severity: {gap['severity']}")


def test_rag_service():
    print("\n" + "=" * 50)
    print(" 4. TESTING RAG SERVICE (O(1) Concept & Pinecone Vector Search)")
    print("=" * 50)

    # Test 4A: O(1) Concept Lookup
    concept_docs = rag_service.search_by_concept("sql_joins", limit=2)
    print(f"✓ Direct O(1) Lookup for 'sql_joins' -> Found {len(concept_docs)} document(s):")
    for doc in concept_docs:
        print(f"   - [{doc['resource_type']}] {doc['title']}")

    # Test 4B: Dense Vector Search against Pinecone
    query = "How do LEFT JOINs handle NULL values when tables don't match?"
    print(f"\n✓ Querying Pinecone with Gemini 'gemini-embedding-2-preview'...")
    print(f"   Query: '{query}'")
    
    vector_results = rag_service.search_by_query(query=query, limit=2)
    assert len(vector_results) > 0, "FAILED: Pinecone vector search returned 0 results. Ensure seed_vector_db.py ran successfully."
    
    print(f"✓ Retrieved {len(vector_results)} matching vector chunk(s) from Pinecone:")
    for res in vector_results:
        print(f"   - Score: {res.get('similarity_score')} | Title: {res['title']}")
        print(f"     Snippet: {res['content_snippet'][:100]}...")


if __name__ == "__main__":
    print("STARTING PHASE 1 FOUNDATION INTEGRATION TESTS...")
    try:
        test_knowledge_graph()
        test_ml_engine()
        test_career_benchmarks()
        test_rag_service()
        print("\n" + "=" * 50)
        print(" 🎉 ALL PHASE 1 TESTS PASSED SUCCESSFULLY! ")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        sys.exit(1)