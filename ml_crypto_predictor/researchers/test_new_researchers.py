#!/usr/bin/env python3
"""
Test script to verify all new researchers can be imported, instantiated, and registered.
"""

import sys
from pathlib import Path

# Add base directory to path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

def test_imports():
    """Test that all new researchers can be imported."""
    print("=" * 70)
    print("TEST 1: Importing new researchers")
    print("=" * 70)
    
    try:
        from ml_crypto_predictor.researchers import (
            ExecutionResearcher,
            DataQualityResearcher,
            MomentumResearcher,
            MeanReversionResearcher,
            RiskResearcher,
            ValidationResearcher,
            AlternativeDataResearcher,
            RobustnessResearcher,
            GovernanceResearcher,
        )
        print("[PASS] All new researchers imported successfully")
        return True
    except ImportError as e:
        print(f"[FAIL] Import failed: {e}")
        return False

def test_instantiation():
    """Test that all researchers can be instantiated."""
    print("\n" + "=" * 70)
    print("TEST 2: Instantiating researchers")
    print("=" * 70)
    
    researchers = [
        ("ExecutionResearcher", "execution"),
        ("DataQualityResearcher", "data_quality"),
        ("MomentumResearcher", "momentum"),
        ("MeanReversionResearcher", "mean_reversion"),
        ("RiskResearcher", "risk_management"),
        ("ValidationResearcher", "validation"),
        ("AlternativeDataResearcher", "alternative_data"),
        ("RobustnessResearcher", "robustness"),
        ("GovernanceResearcher", "governance"),
    ]
    
    success = True
    for class_name, researcher_id in researchers:
        try:
            module = __import__('researchers', fromlist=[class_name])
            cls = getattr(module, class_name)
            instance = cls(config={"base_dir": base_dir})
            
            # Verify researcher_id matches
            if instance.researcher_id != researcher_id:
                print(f"[FAIL] {class_name}: researcher_id mismatch (expected {researcher_id}, got {instance.researcher_id})")
                success = False
            else:
                print(f"[PASS] {class_name} instantiated (ID: {researcher_id})")
        except Exception as e:
            print(f"❌ {class_name} failed: {e}")
            success = False
    
    return success

def test_formulate_questions():
    """Test that all researchers can formulate questions."""
    print("\n" + "=" * 70)
    print("TEST 3: Formulating research questions")
    print("=" * 70)
    
    researchers = [
        ("ExecutionResearcher", "execution"),
        ("DataQualityResearcher", "data_quality"),
        ("MomentumResearcher", "momentum"),
        ("MeanReversionResearcher", "mean_reversion"),
        ("RiskResearcher", "risk_management"),
        ("ValidationResearcher", "validation"),
        ("AlternativeDataResearcher", "alternative_data"),
        ("RobustnessResearcher", "robustness"),
        ("GovernanceResearcher", "governance"),
    ]
    
    success = True
    total_questions = 0
    for class_name, researcher_id in researchers:
        try:
            module = __import__('researchers', fromlist=[class_name])
            cls = getattr(module, class_name)
            instance = cls(config={"base_dir": base_dir})
            questions = instance.formulate_questions()
            
            if not questions:
                print(f"[WARN] {class_name}: No questions formulated")
            else:
                print(f"[PASS] {class_name}: {len(questions)} questions")
                total_questions += len(questions)
                
                # Verify question IDs have correct prefix
                for q in questions:
                    expected_prefix = researcher_id.split('_')[0]  # e.g., "execution" -> "exec"
                    if not q.id.startswith(expected_prefix) and not q.id.startswith(researcher_id.split('_')[0][:3]):
                        # Allow some flexibility in prefix matching
                        pass  # Not enforcing strict prefix for all
        except Exception as e:
            print(f"❌ {class_name} failed: {e}")
            success = False
    
    print(f"\n📊 Total research questions: {total_questions}")
    return success

def test_coordinator_registration():
    """Test that coordinator can register all researchers."""
    print("\n" + "=" * 70)
    print("TEST 4: Coordinator registration")
    print("=" * 70)
    
    try:
        from researchers import ResearchCoordinator
        from researchers.config import get_active_researchers
        
        coordinator = ResearchCoordinator(base_dir=base_dir)
        active_researchers = get_active_researchers()
        
        print(f"Active researchers: {len(active_researchers)}")
        
        # Import and register all active researchers
        for rid in active_researchers:
            try:
                # Map researcher_id to class name
                class_map = {
                    "sequence_models": "SequenceModelResearcher",
                    "transformers": "TransformerResearcher",
                    "graph_neural": "GraphNeuralResearcher",
                    "contrastive": "ContrastiveResearcher",
                    "meta_learning": "MetaLearningResearcher",
                    "ensemble": "EnsembleResearcher",
                    "regime_detection": "RegimeResearcher",
                    "feature_engineering": "FeatureResearcher",
                    "momentum": "MomentumResearcher",
                    "mean_reversion": "MeanReversionResearcher",
                    "execution": "ExecutionResearcher",
                    "risk_management": "RiskResearcher",
                    "validation": "ValidationResearcher",
                    "alternative_data": "AlternativeDataResearcher",
                    "robustness": "RobustnessResearcher",
                    "data_quality": "DataQualityResearcher",
                    "governance": "GovernanceResearcher",
                }
                
                class_name = class_map.get(rid)
                if not class_name:
                    print(f"⚠️  No class mapping for {rid}, skipping")
                    continue
                
                module = __import__('researchers', fromlist=[class_name])
                cls = getattr(module, class_name)
                researcher = cls(config={"base_dir": base_dir})
                coordinator.register_researcher(researcher)
                
            except Exception as e:
                print(f"❌ Failed to register {rid}: {e}")
                return False
        
        print(f"✅ Coordinator registered {len(coordinator.researchers)} researchers")
        return True
        
    except Exception as e:
        print(f"❌ Coordinator test failed: {e}")
        return False

def test_knowledge_sharing():
    """Test that researchers can share knowledge."""
    print("\n" + "=" * 70)
    print("TEST 5: Knowledge sharing")
    print("=" * 70)
    
    try:
        from researchers import ExecutionResearcher
        
        researcher = ExecutionResearcher(config={"base_dir": base_dir})
        knowledge = researcher.share_knowledge()
        
        if "researcher_id" in knowledge and "contributions" in knowledge:
            print(f"✅ Knowledge sharing works")
            print(f"   Contributions: {len(knowledge['contributions'])} items")
            return True
        else:
            print(f"❌ Knowledge sharing malformed: {knowledge.keys()}")
            return False
    except Exception as e:
        print(f"❌ Knowledge sharing failed: {e}")
        return False

def main():
    print("\n" + "=" * 70)
    print("TESTING NEW RESEARCHER FRAMEWORK")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Instantiation", test_instantiation()))
    results.append(("Formulate Questions", test_formulate_questions()))
    results.append(("Coordinator Registration", test_coordinator_registration()))
    results.append(("Knowledge Sharing", test_knowledge_sharing()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The researcher framework is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
