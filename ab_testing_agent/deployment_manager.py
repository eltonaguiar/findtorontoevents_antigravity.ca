import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

try:
    from .database import Deployment
except ImportError:
    from database import Deployment

logger = logging.getLogger(__name__)

class DeploymentStatus(Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"

class DeploymentManager:
    """Manages safe deployment of winning variants"""

    def __init__(self, db_session, production_url: str, staging_url: str = None):
        self.db = db_session
        self.production_url = production_url
        self.staging_url = staging_url

    def gradual_rollout(self, experiment_id: int, winner_variant: str,
                       steps: List[float] = [0.1, 0.25, 0.5, 1.0],
                       monitoring_periods: int = 24) -> bool:
        """
        Perform gradual rollout of winning variant

        Args:
            experiment_id: ID of the completed experiment
            winner_variant: Name of the winning variant
            steps: List of traffic percentages to roll out (0.1 = 10%)
            monitoring_periods: Hours to monitor each step
        """
        try:
            for traffic_pct in steps:
                logger.info(f"Rolling out {winner_variant} to {traffic_pct*100}% traffic")

                # Create deployment record
                deployment = Deployment(
                    experiment_id=experiment_id,
                    variant=winner_variant,
                    traffic_percentage=traffic_pct,
                    status=DeploymentStatus.DEPLOYING.value
                )
                self.db.add(deployment)
                self.db.commit()

                # Perform deployment
                success = self._deploy_variant(winner_variant, traffic_pct)

                if not success:
                    logger.error(f"Deployment failed at {traffic_pct*100}% traffic")
                    self._rollback_deployment(deployment.id)
                    return False

                deployment.status = DeploymentStatus.DEPLOYED.value
                deployment.deployed_at = datetime.utcnow()
                self.db.commit()

                # Monitor for issues
                if not self._monitor_deployment(deployment.id, monitoring_periods):
                    logger.warning(f"Issues detected at {traffic_pct*100}% traffic, rolling back")
                    self._rollback_deployment(deployment.id)
                    return False

            logger.info(f"Successfully completed rollout of {winner_variant}")
            return True

        except Exception as e:
            logger.error(f"Error during gradual rollout: {str(e)}")
            return False

    def _deploy_variant(self, variant: str, traffic_percentage: float) -> bool:
        """Deploy a variant to production with specified traffic percentage"""
        try:
            # This would integrate with your deployment system
            # For now, simulate API call to deployment service
            payload = {
                'variant': variant,
                'traffic_percentage': traffic_percentage,
                'timestamp': datetime.utcnow().isoformat()
            }

            # Simulate deployment API call
            response = requests.post(
                f"{self.production_url}/api/deploy",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Successfully deployed {variant} at {traffic_percentage*100}% traffic")
                return True
            else:
                logger.error(f"Deployment API returned {response.status_code}: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error deploying variant: {str(e)}")
            return False

    def _monitor_deployment(self, deployment_id: int, hours: int) -> bool:
        """Monitor deployment for issues"""
        try:
            # Check key metrics for degradation
            # This would integrate with monitoring system
            monitoring_data = self._get_monitoring_data(deployment_id, hours)

            # Simple checks - customize based on your metrics
            error_rate_threshold = 0.05  # 5% error rate
            latency_threshold = 2.0  # 2x latency increase

            if monitoring_data['error_rate'] > error_rate_threshold:
                logger.warning(f"Error rate {monitoring_data['error_rate']} exceeds threshold")
                return False

            if monitoring_data['latency_ratio'] > latency_threshold:
                logger.warning(f"Latency ratio {monitoring_data['latency_ratio']} exceeds threshold")
                return False

            logger.info(f"Deployment monitoring passed for deployment {deployment_id}")
            return True

        except Exception as e:
            logger.error(f"Error monitoring deployment: {str(e)}")
            return False

    def _get_monitoring_data(self, deployment_id: int, hours: int) -> Dict:
        """Get monitoring data for deployment"""
        # Simulate monitoring API call
        # In real implementation, integrate with your monitoring system
        return {
            'error_rate': 0.02,  # 2%
            'latency_ratio': 1.1,  # 10% increase
            'throughput_ratio': 0.95  # 5% decrease
        }

    def _rollback_deployment(self, deployment_id: int) -> bool:
        """Rollback a deployment"""
        try:
            deployment = self.db.query(Deployment).filter_by(id=deployment_id).first()
            if not deployment:
                return False

            # Rollback to previous version
            payload = {
                'deployment_id': deployment_id,
                'action': 'rollback',
                'timestamp': datetime.utcnow().isoformat()
            }

            response = requests.post(
                f"{self.production_url}/api/rollback",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                deployment.status = DeploymentStatus.ROLLED_BACK.value
                self.db.commit()
                logger.info(f"Successfully rolled back deployment {deployment_id}")
                return True
            else:
                logger.error(f"Rollback API returned {response.status_code}: {response.text}")
                deployment.status = DeploymentStatus.FAILED.value
                self.db.commit()
                return False

        except Exception as e:
            logger.error(f"Error rolling back deployment: {str(e)}")
            return False

    def emergency_rollback(self, experiment_id: int) -> bool:
        """Emergency rollback to baseline for an experiment"""
        try:
            # Find latest deployment for this experiment
            latest_deployment = self.db.query(Deployment).filter_by(
                experiment_id=experiment_id
            ).order_by(Deployment.deployed_at.desc()).first()

            if not latest_deployment:
                logger.warning(f"No deployments found for experiment {experiment_id}")
                return False

            return self._rollback_deployment(latest_deployment.id)

        except Exception as e:
            logger.error(f"Error in emergency rollback: {str(e)}")
            return False

    def get_deployment_status(self, experiment_id: int) -> List[Dict]:
        """Get deployment history for an experiment"""
        deployments = self.db.query(Deployment).filter_by(
            experiment_id=experiment_id
        ).order_by(Deployment.created_at).all()

        return [{
            'id': d.id,
            'variant': d.variant,
            'traffic_percentage': d.traffic_percentage,
            'status': d.status,
            'deployed_at': d.deployed_at.isoformat() if d.deployed_at else None,
            'created_at': d.created_at.isoformat()
        } for d in deployments]