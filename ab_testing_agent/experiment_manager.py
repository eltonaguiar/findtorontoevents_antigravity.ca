import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from .database import Experiment, Observation, Deployment
    from .statistics import StatisticalAnalyzer
except ImportError:
    from database import Experiment, Observation, Deployment
    from statistics import StatisticalAnalyzer

logger = logging.getLogger(__name__)

class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"

class ExperimentManager:
    """Manages A/B testing experiments"""

    def __init__(self, db_session, statistical_analyzer: StatisticalAnalyzer = None):
        self.db = db_session
        self.stats_analyzer = statistical_analyzer or StatisticalAnalyzer()

    def create_experiment(self, name: str, description: str, variants: List[Dict],
                         metrics: List[str], target_metric: str,
                         significance_level: float = 0.05,
                         minimum_effect_size: float = 0.01) -> Experiment:
        """
        Create a new A/B testing experiment

        Args:
            name: Experiment name
            description: Experiment description
            variants: List of variant dicts [{'name': 'A', 'traffic_percentage': 50}, ...]
            metrics: List of metric names to track
            target_metric: Primary metric for winner determination
            significance_level: Statistical significance threshold
            minimum_effect_size: Minimum detectable effect size
        """
        # Calculate minimum sample size
        min_sample_size = self.stats_analyzer.calculate_sample_size(minimum_effect_size)

        experiment = Experiment(
            name=name,
            description=description,
            variants=json.dumps(variants),
            metrics=json.dumps(metrics),
            target_metric=target_metric,
            significance_level=significance_level,
            minimum_sample_size=min_sample_size,
            status=ExperimentStatus.DRAFT.value
        )

        self.db.add(experiment)
        self.db.commit()
        logger.info(f"Created experiment: {name} (ID: {experiment.id})")
        return experiment

    def start_experiment(self, experiment_id: int) -> bool:
        """Start an experiment"""
        experiment = self.db.query(Experiment).filter_by(id=experiment_id).first()
        if not experiment:
            logger.error(f"Experiment {experiment_id} not found")
            return False

        if experiment.status != ExperimentStatus.DRAFT.value:
            logger.error(f"Experiment {experiment_id} is not in draft status")
            return False

        experiment.status = ExperimentStatus.RUNNING.value
        experiment.start_date = datetime.utcnow()
        self.db.commit()
        logger.info(f"Started experiment: {experiment.name} (ID: {experiment_id})")
        return True

    def stop_experiment(self, experiment_id: int) -> bool:
        """Stop an experiment"""
        experiment = self.db.query(Experiment).filter_by(id=experiment_id).first()
        if not experiment:
            logger.error(f"Experiment {experiment_id} not found")
            return False

        experiment.status = ExperimentStatus.STOPPED.value
        experiment.end_date = datetime.utcnow()
        self.db.commit()
        logger.info(f"Stopped experiment: {experiment.name} (ID: {experiment_id})")
        return True

    def record_observation(self, experiment_id: int, variant: str, metrics_data: Dict[str, float]) -> bool:
        """Record an observation for an experiment"""
        experiment = self.db.query(Experiment).filter_by(id=experiment_id).first()
        if not experiment:
            logger.error(f"Experiment {experiment_id} not found")
            return False

        if experiment.status != ExperimentStatus.RUNNING.value:
            logger.warning(f"Experiment {experiment_id} is not running")
            return False

        # Validate variant
        variants = json.loads(experiment.variants)
        variant_names = [v['name'] for v in variants]
        if variant not in variant_names:
            logger.error(f"Invalid variant {variant} for experiment {experiment_id}")
            return False

        observation = Observation(
            experiment_id=experiment_id,
            variant=variant,
            metrics_data=json.dumps(metrics_data)
        )

        self.db.add(observation)
        self.db.commit()
        logger.debug(f"Recorded observation for experiment {experiment_id}, variant {variant}")
        return True

    def analyze_experiment(self, experiment_id: int) -> Dict[str, Any]:
        """Analyze experiment results"""
        experiment = self.db.query(Experiment).filter_by(id=experiment_id).first()
        if not experiment:
            return {'error': 'Experiment not found'}

        # Get all observations
        observations = self.db.query(Observation).filter_by(experiment_id=experiment_id).all()

        if not observations:
            return {'status': 'insufficient_data', 'message': 'No observations recorded yet'}

        # Group observations by variant
        variant_data = {}
        for obs in observations:
            metrics = json.loads(obs.metrics_data)
            variant = obs.variant
            if variant not in variant_data:
                variant_data[variant] = []
            variant_data[variant].append(metrics)

        target_metric = experiment.target_metric

        # Extract target metric values
        group_a_data = [obs[target_metric] for obs in variant_data.get('A', [])]
        group_b_data = [obs[target_metric] for obs in variant_data.get('B', [])]

        if len(group_a_data) < 10 or len(group_b_data) < 10:
            return {
                'status': 'insufficient_data',
                'message': f'Need at least 10 observations per variant. A: {len(group_a_data)}, B: {len(group_b_data)}'
            }

        # Perform statistical tests
        t_test_results = self.stats_analyzer.perform_t_test(group_a_data, group_b_data)
        bayesian_results = self.stats_analyzer.bayesian_analysis(group_a_data, group_b_data)

        # Check sample size adequacy
        current_n = min(len(group_a_data), len(group_b_data))
        sample_check = self.stats_analyzer.check_sample_size_adequacy(
            current_n, experiment.minimum_sample_size
        )

        # Determine winner
        winner = None
        if t_test_results['significant']:
            if t_test_results['mean_difference'] > 0:
                winner = 'A'
            else:
                winner = 'B'

        # Update experiment
        experiment.winner = winner
        experiment.confidence_level = 1 - t_test_results['p_value']
        experiment.effect_size = t_test_results['effect_size']
        self.db.commit()

        return {
            'status': 'analyzed',
            'winner': winner,
            't_test': t_test_results,
            'bayesian': bayesian_results,
            'sample_size_check': sample_check,
            'total_observations': len(observations),
            'variant_counts': {k: len(v) for k, v in variant_data.items()}
        }

    def get_experiment_status(self, experiment_id: int) -> Dict[str, Any]:
        """Get current status of an experiment"""
        experiment = self.db.query(Experiment).filter_by(id=experiment_id).first()
        if not experiment:
            return {'error': 'Experiment not found'}

        analysis = self.analyze_experiment(experiment_id)

        return {
            'id': experiment.id,
            'name': experiment.name,
            'status': experiment.status,
            'start_date': experiment.start_date.isoformat() if experiment.start_date else None,
            'end_date': experiment.end_date.isoformat() if experiment.end_date else None,
            'variants': json.loads(experiment.variants),
            'metrics': json.loads(experiment.metrics),
            'target_metric': experiment.target_metric,
            'analysis': analysis
        }

    def list_experiments(self, status: Optional[str] = None) -> List[Dict]:
        """List all experiments, optionally filtered by status"""
        query = self.db.query(Experiment)
        if status:
            query = query.filter_by(status=status)

        experiments = query.all()
        return [{
            'id': exp.id,
            'name': exp.name,
            'status': exp.status,
            'start_date': exp.start_date.isoformat() if exp.start_date else None,
            'end_date': exp.end_date.isoformat() if exp.end_date else None,
            'winner': exp.winner
        } for exp in experiments]