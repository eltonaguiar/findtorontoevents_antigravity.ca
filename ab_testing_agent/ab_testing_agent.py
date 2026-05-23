import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from apscheduler.schedulers.background import BackgroundScheduler

try:
    from .database import init_db
    from .experiment_manager import ExperimentManager
    from .deployment_manager import DeploymentManager
    from .statistics import StatisticalAnalyzer
    from .config import Config
except ImportError:
    from database import init_db
    from experiment_manager import ExperimentManager
    from deployment_manager import DeploymentManager
    from statistics import StatisticalAnalyzer
    from config import Config

logger = logging.getLogger(__name__)

class ABTestingAgent:
    """
    Main A/B Testing Agent that orchestrates all components
    """

    def __init__(self, config: Config):
        self.config = config

        # Initialize database
        self.db_session = init_db(config.DATABASE_URL)

        # Initialize components
        self.stats_analyzer = StatisticalAnalyzer(
            significance_level=config.DEFAULT_SIGNIFICANCE_LEVEL
        )
        self.experiment_manager = ExperimentManager(
            self.db_session, self.stats_analyzer
        )
        self.deployment_manager = DeploymentManager(
            self.db_session,
            config.PRODUCTION_URL,
            config.STAGING_URL
        )

        # Monitoring and alerting
        self.alerts_enabled = bool(config.ALERT_EMAIL)
        self.scheduler = BackgroundScheduler()

        # Setup logging
        self._setup_logging()

        logger.info("A/B Testing Agent initialized")

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.LOG_FILE),
                logging.StreamHandler()
            ]
        )

    def start_monitoring(self):
        """Start background monitoring and alerting"""
        # Monitor running experiments every hour
        self.scheduler.add_job(
            self._monitor_experiments,
            'interval',
            hours=1,
            id='experiment_monitor'
        )

        # Check for completed experiments daily
        self.scheduler.add_job(
            self._check_completed_experiments,
            'interval',
            hours=24,
            id='completion_check'
        )

        # Monitor deployments every 30 minutes
        self.scheduler.add_job(
            self._monitor_deployments,
            'interval',
            minutes=30,
            id='deployment_monitor'
        )

        self.scheduler.start()
        logger.info("Background monitoring started")

    def stop_monitoring(self):
        """Stop background monitoring"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        logger.info("Background monitoring stopped")

    def _monitor_experiments(self):
        """Monitor running experiments for issues"""
        try:
            experiments = self.experiment_manager.list_experiments(status='running')

            for exp in experiments:
                status = self.experiment_manager.get_experiment_status(exp['id'])
                analysis = status.get('analysis', {})

                # Check for statistical significance
                if analysis.get('status') == 'analyzed':
                    t_test = analysis.get('t_test', {})
                    if t_test.get('significant', False):
                        self._send_alert(
                            f"Experiment {exp['name']} shows statistical significance",
                            f"p-value: {t_test.get('p_value'):.4f}\n"
                            f"Effect size: {t_test.get('effect_size'):.3f}\n"
                            f"Winner: {analysis.get('winner')}"
                        )

                # Check sample size adequacy
                sample_check = analysis.get('sample_size_check', {})
                if not sample_check.get('is_adequate', True):
                    completion = sample_check.get('completion_percentage', 0)
                    if completion > 80:  # Alert when close to adequate sample
                        self._send_alert(
                            f"Experiment {exp['name']} approaching adequate sample size",
                            f"Current completion: {completion:.1f}%"
                        )

        except Exception as e:
            logger.error(f"Error in experiment monitoring: {str(e)}")

    def _check_completed_experiments(self):
        """Check for experiments that should be completed"""
        try:
            experiments = self.experiment_manager.list_experiments(status='running')

            for exp in experiments:
                status = self.experiment_manager.get_experiment_status(exp['id'])
                analysis = status.get('analysis', {})

                # Auto-complete experiments with adequate sample and significance
                if (analysis.get('status') == 'analyzed' and
                    analysis.get('sample_size_check', {}).get('is_adequate', False) and
                    analysis.get('t_test', {}).get('significant', False)):

                    winner = analysis.get('winner')
                    if winner:
                        self._send_alert(
                            f"Experiment {exp['name']} ready for deployment",
                            f"Winner: {winner}\n"
                            f"p-value: {analysis['t_test']['p_value']:.4f}\n"
                            f"Consider deploying the winning variant."
                        )

        except Exception as e:
            logger.error(f"Error checking completed experiments: {str(e)}")

    def _monitor_deployments(self):
        """Monitor active deployments"""
        try:
            # This would check deployment status and alert on issues
            # For now, just log that monitoring is running
            logger.debug("Deployment monitoring check completed")
        except Exception as e:
            logger.error(f"Error in deployment monitoring: {str(e)}")

    def _send_alert(self, subject: str, message: str):
        """Send email alert"""
        if not self.alerts_enabled:
            logger.info(f"Alert (not sent): {subject}")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.ALERT_EMAIL
            msg['To'] = self.config.ALERT_EMAIL
            msg['Subject'] = f"A/B Testing Alert: {subject}"

            msg.attach(MIMEText(message, 'plain'))

            server = smtplib.SMTP(self.config.SMTP_SERVER)
            server.send_message(msg)
            server.quit()

            logger.info(f"Alert sent: {subject}")

        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")

    def create_experiment(self, name: str, description: str, variants: List[Dict],
                         metrics: List[str], target_metric: str,
                         significance_level: float = None,
                         minimum_effect_size: float = None) -> int:
        """
        Create a new A/B testing experiment

        Returns experiment ID
        """
        sig_level = significance_level or self.config.DEFAULT_SIGNIFICANCE_LEVEL
        min_effect = minimum_effect_size or self.config.DEFAULT_MINIMUM_DETECTABLE_EFFECT

        experiment = self.experiment_manager.create_experiment(
            name=name,
            description=description,
            variants=variants,
            metrics=metrics,
            target_metric=target_metric,
            significance_level=sig_level,
            minimum_effect_size=min_effect
        )

        logger.info(f"Created experiment: {name} (ID: {experiment.id})")
        return experiment.id

    def start_experiment(self, experiment_id: int) -> bool:
        """Start an experiment"""
        return self.experiment_manager.start_experiment(experiment_id)

    def record_observation(self, experiment_id: int, variant: str, metrics_data: Dict) -> bool:
        """Record an observation for an experiment"""
        return self.experiment_manager.record_observation(experiment_id, variant, metrics_data)

    def analyze_experiment(self, experiment_id: int) -> Dict:
        """Analyze experiment results"""
        return self.experiment_manager.analyze_experiment(experiment_id)

    def deploy_winner(self, experiment_id: int, winner_variant: str,
                     rollout_steps: List[float] = None,
                     monitoring_periods: int = 24) -> bool:
        """Deploy the winning variant with gradual rollout"""
        steps = rollout_steps or [0.1, 0.25, 0.5, 1.0]
        return self.deployment_manager.gradual_rollout(
            experiment_id, winner_variant, steps, monitoring_periods
        )

    def emergency_rollback(self, experiment_id: int) -> bool:
        """Emergency rollback for an experiment"""
        return self.deployment_manager.emergency_rollback(experiment_id)

    def get_experiment_status(self, experiment_id: int) -> Dict:
        """Get comprehensive experiment status"""
        return self.experiment_manager.get_experiment_status(experiment_id)

    def list_experiments(self, status: Optional[str] = None) -> List[Dict]:
        """List experiments, optionally filtered by status"""
        return self.experiment_manager.list_experiments(status)

    def calculate_sample_size(self, effect_size: float, std_dev: float = None) -> int:
        """Calculate required sample size for statistical power"""
        return self.stats_analyzer.calculate_sample_size(effect_size, std_dev)

    def run_api_server(self, host: str = None, port: int = None):
        """Run the API server"""
        from .api import ABTestingAPI
        api = ABTestingAPI(self.config)
        api.run(host=host, port=port)

    def run_dashboard(self, host: str = None, port: int = None):
        """Run the web dashboard"""
        from .dashboard import ABTestingDashboard
        dashboard = ABTestingDashboard(self.config)
        dashboard.run(host=host, port=port)

# Convenience functions for external use
def create_agent(config: Config = None) -> ABTestingAgent:
    """Create and return an A/B Testing Agent instance"""
    config = config or Config()
    return ABTestingAgent(config)

def quick_experiment(name: str, variants: List[str], target_metric: str,
                    config: Config = None) -> int:
    """
    Quick experiment setup with default settings

    Args:
        name: Experiment name
        variants: List of variant names
        target_metric: Metric to optimize

    Returns:
        Experiment ID
    """
    config = config or Config()

    # Create variant dicts with equal traffic
    traffic_pct = 100 / len(variants)
    variant_dicts = [{'name': v, 'traffic_percentage': traffic_pct} for v in variants]

    agent = create_agent(config)
    exp_id = agent.create_experiment(
        name=name,
        description=f"Quick experiment with variants: {', '.join(variants)}",
        variants=variant_dicts,
        metrics=[target_metric],
        target_metric=target_metric
    )

    return exp_id