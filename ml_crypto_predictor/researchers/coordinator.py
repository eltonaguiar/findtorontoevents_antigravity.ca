"""
ResearchCoordinator — Orchestrates Multi-Researcher Collaboration
=================================================================

Manages the workflow of multiple specialized researchers, ensuring:
  - Efficient allocation of research questions
  - Knowledge sharing between researchers
  - Conflict resolution when researchers overlap
  - Synthesis of cross-disciplinary findings
  - Prioritization based on strategic importance

The coordinator acts as a "principal investigator" overseeing the research lab.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json
from collections import defaultdict

from .base import Researcher, ResearchQuestion, ResearchResult


class ResearchCoordinator:
    """
    Orchestrates multiple researchers to tackle a comprehensive research agenda.
    
    Responsibilities:
      1. Register researchers with their specializations
      2. Assign research questions to appropriate specialists
      3. Facilitate knowledge sharing between researchers
      4. Track progress and dependencies
      5. Synthesize final recommendations
      6. Resolve conflicts/overlaps between researchers
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the research coordinator.
        
        Args:
            base_dir: Base directory for all research outputs
        """
        self.base_dir = base_dir or Path("ml_crypto_predictor")
        self.researchers: Dict[str, Researcher] = {}
        self.all_questions: Dict[str, ResearchQuestion] = {}
        self.results: Dict[str, ResearchResult] = {}
        self.knowledge_graph: Dict[str, List[str]] = defaultdict(list)  # question_id → [related_ids]
        
        # Tracking
        self.assignment_log: List[Dict] = []
        self.conflicts_detected: int = 0
        
        # Results directory
        self.results_dir = self.base_dir / "results" / "coordinator"
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def register_researcher(self, researcher: Researcher) -> bool:
        """
        Register a researcher with the coordinator.
        
        Args:
            researcher: Researcher instance to register
            
        Returns:
            True if registration successful, False if duplicate ID
        """
        if researcher.researcher_id in self.researchers:
            print(f"[Coordinator] Researcher {researcher.researcher_id} already registered")
            return False
        
        self.researchers[researcher.researcher_id] = researcher
        print(f"[Coordinator] Registered: {researcher.name} ({researcher.specialization})")
        return True
    
    def add_research_question(self, question: ResearchQuestion,
                            assignee: Optional[str] = None) -> str:
        """
        Add a research question to the agenda.
        
        Args:
            question: Research question to add
            assignee: Optional researcher ID to assign directly
            
        Returns:
            Question ID
        """
        self.all_questions[question.id] = question
        
        if assignee:
            self._assign_question(question.id, assignee)
        else:
            # Auto-assign based on specialization match
            best_match = self._find_best_researcher(question)
            if best_match:
                self._assign_question(question.id, best_match)
        
        return question.id
    
    def _find_best_researcher(self, question: ResearchQuestion) -> Optional[str]:
        """
        Find the most suitable researcher for a question.
        
        Uses keyword matching between question description/tags and researcher specialization.
        """
        best_score = -1
        best_id = None
        
        question_text = f"{question.title} {question.description}".lower()
        
        for rid, researcher in self.researchers.items():
            score = 0
            spec = researcher.specialization.lower()
            
            # Direct keyword matches
            keywords = spec.split() + [researcher.researcher_id]
            for kw in keywords:
                if kw.lower() in question_text:
                    score += 1
            
            # Check literature alignment
            for paper in researcher.literature:
                if any(word.lower() in question_text for word in paper.split()[:3]):
                    score += 0.5
            
            if score > best_score:
                best_score = score
                best_id = rid
        
        return best_id if best_score > 0 else None
    
    def _assign_question(self, question_id: str, researcher_id: str):
        """Assign a question to a specific researcher."""
        if researcher_id not in self.researchers:
            print(f"[Coordinator] Cannot assign: researcher {researcher_id} not found")
            return
        
        question = self.all_questions[question_id]
        researcher = self.researchers[researcher_id]
        
        # Check dependencies
        for dep in question.dependencies:
            if dep not in self.results:
                print(f"[Coordinator] Dependency {dep} not yet completed for {question_id}")
                return
        
        # Log assignment
        self.assignment_log.append({
            "question_id": question_id,
            "researcher": researcher_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "priority": question.priority,
        })
        
        print(f"[Coordinator] Assigned '{question.title[:50]}' → {researcher.name}")
    
    def run_investigation(self, question_ids: Optional[List[str]] = None,
                         parallel: bool = False) -> Dict[str, ResearchResult]:
        """
        Execute research investigations.
        
        Args:
            question_ids: Specific questions to investigate (None = all pending)
            parallel: Whether to run researchers in parallel (not yet implemented)
            
        Returns:
            Dictionary of results by question_id
        """
        if question_ids is None:
            # Get all questions that have assignments
            assigned = {log["question_id"] for log in self.assignment_log}
            question_ids = [qid for qid in self.all_questions.keys() if qid in assigned]
        
        results = {}
        
        for qid in question_ids:
            # Find assigned researcher
            assignment = next(
                (log for log in reversed(self.assignment_log) if log["question_id"] == qid),
                None
            )
            if not assignment:
                print(f"[Coordinator] No assignment found for {qid}")
                continue
            
            researcher_id = assignment["researcher"]
            researcher = self.researchers[researcher_id]
            question = self.all_questions[qid]
            
            print(f"\n{'='*70}")
            print(f"[Coordinator] Launching investigation: {question.title}")
            print(f"  Lead: {researcher.name}")
            print(f"{'='*70}")
            
            try:
                # Run full investigation
                result = researcher.run_full_investigation(question_id=qid)
                results.update(result)
                self.results.update(result)
                
                print(f"[Coordinator] ✓ Completed: {qid}")
                
                # Check for related questions that can now proceed
                self._check_dependency_satisfaction(qid)
                
            except Exception as e:
                print(f"[Coordinator] ✗ Failed: {qid} — {e}")
        
        # Generate final synthesis
        self._generate_synthesis_report()
        
        return results
    
    def _check_dependency_satisfaction(self, completed_qid: str):
        """Check if any pending questions had this as a dependency."""
        for qid, question in self.all_questions.items():
            if completed_qid in question.dependencies and qid not in self.results:
                print(f"[Coordinator] Dependency satisfied: {qid} can now proceed")
    
    def get_cross_insights(self, topic: str) -> Dict[str, Any]:
        """
        Gather insights from all researchers on a specific topic.
        
        Args:
            topic: Topic to query (e.g., "attention", "lstm", "regime")
            
        Returns:
            Consolidated insights from multiple perspectives
        """
        all_insights = {}
        
        for rid, researcher in self.researchers.items():
            insights = researcher.get_relevant_knowledge(topic)
            if insights:
                all_insights[rid] = {
                    "researcher": researcher.name,
                    "specialization": researcher.specialization,
                    "insights": insights,
                }
        
        return all_insights
    
    def _generate_synthesis_report(self):
        """Generate a comprehensive synthesis of all research findings."""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_questions": len(self.all_questions),
            "completed": len(self.results),
            "researchers": list(self.researchers.keys()),
            "findings_by_researcher": {},
            "cross_insights": {},
            "recommendations": {},
        }
        
        # Organize by researcher
        for rid, researcher in self.researchers.items():
            researcher_results = [
                r for qid, r in self.results.items()
                if r.researcher_id == rid
            ]
            report["findings_by_researcher"][rid] = {
                "name": researcher.name,
                "specialization": researcher.specialization,
                "completed": len(researcher_results),
                "avg_confidence": (
                    sum(r.confidence for r in researcher_results) / len(researcher_results)
                    if researcher_results else 0
                ),
            }
        
        # Cross-researcher insights
        for topic in ["ensemble", "regime", "feature", "validation"]:
            report["cross_insights"][topic] = self.get_cross_insights(topic)
        
        # Consolidated recommendations
        all_recs = defaultdict(list)
        for result in self.results.values():
            for qid, rec in result.recommendations.items():
                all_recs[qid].append(rec)
        
        report["recommendations"] = dict(all_recs)
        
        # Save report
        report_path = self.results_dir / "synthesis_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n[Coordinator] Synthesis report saved: {report_path}")
        
        # Print summary
        print("\n" + "="*70)
        print("RESEARCH PROGRAM SUMMARY")
        print("="*70)
        print(f"Total questions: {report['total_questions']}")
        print(f"Completed: {report['completed']}")
        print("\nBy researcher:")
        for rid, info in report["findings_by_researcher"].items():
            print(f"  {info['name']}: {info['completed']} questions, "
                  f"avg confidence={info['avg_confidence']:.1%}")
        print("="*70)
        
        return report
    
    def save_program_state(self):
        """Save complete state of the research program."""
        state = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "questions": {qid: {
                "id": q.id,
                "title": q.title,
                "priority": q.priority,
                "dependencies": q.dependencies,
                "status": "completed" if qid in self.results else "pending",
            } for qid, q in self.all_questions.items()},
            "assignments": self.assignment_log,
            "results_summary": {
                qid: {
                    "confidence": r.confidence,
                    "reproducible": r.reproducible,
                    "metrics": r.metrics,
                } for qid, r in self.results.items()
            },
        }
        
        state_path = self.results_dir / "program_state.json"
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2, default=str)
        
        print(f"[Coordinator] Program state saved: {state_path}")
    
    def load_program_state(self):
        """Load previous research program state."""
        state_path = self.results_dir / "program_state.json"
        if not state_path.exists():
            print("[Coordinator] No previous state found")
            return
        
        with open(state_path) as f:
            state = json.load(f)
        
        print(f"[Coordinator] Loaded state from {state['saved_at']}")
        print(f"  Questions: {len(state['questions'])}")
        print(f"  Completed: {len(state['results_summary'])}")
