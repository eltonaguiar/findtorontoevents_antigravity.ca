from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
from datetime import datetime

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

class ABTestingAPI:
    """REST API for A/B Testing Agent"""

    def __init__(self, config: Config):
        self.config = config
        self.app = Flask(__name__)
        CORS(self.app)

        # Initialize components
        self.db_session = init_db(config.DATABASE_URL)
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

        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.route('/api/experiments', methods=['GET'])
        def list_experiments():
            status = request.args.get('status')
            experiments = self.experiment_manager.list_experiments(status)
            return jsonify({'experiments': experiments})

        @self.app.route('/api/experiments', methods=['POST'])
        def create_experiment():
            data = request.get_json()

            required_fields = ['name', 'variants', 'metrics', 'target_metric']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            try:
                experiment = self.experiment_manager.create_experiment(
                    name=data['name'],
                    description=data.get('description', ''),
                    variants=data['variants'],
                    metrics=data['metrics'],
                    target_metric=data['target_metric'],
                    significance_level=data.get('significance_level', self.config.DEFAULT_SIGNIFICANCE_LEVEL),
                    minimum_effect_size=data.get('minimum_effect_size', self.config.DEFAULT_MINIMUM_DETECTABLE_EFFECT)
                )

                return jsonify({
                    'id': experiment.id,
                    'message': 'Experiment created successfully'
                }), 201

            except Exception as e:
                logger.error(f"Error creating experiment: {str(e)}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/experiments/<int:experiment_id>/start', methods=['POST'])
        def start_experiment(experiment_id):
            success = self.experiment_manager.start_experiment(experiment_id)
            if success:
                return jsonify({'message': 'Experiment started successfully'})
            else:
                return jsonify({'error': 'Failed to start experiment'}), 400

        @self.app.route('/api/experiments/<int:experiment_id>/stop', methods=['POST'])
        def stop_experiment(experiment_id):
            success = self.experiment_manager.stop_experiment(experiment_id)
            if success:
                return jsonify({'message': 'Experiment stopped successfully'})
            else:
                return jsonify({'error': 'Failed to stop experiment'}), 400

        @self.app.route('/api/experiments/<int:experiment_id>/observations', methods=['POST'])
        def record_observation(experiment_id):
            data = request.get_json()

            required_fields = ['variant', 'metrics']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400

            success = self.experiment_manager.record_observation(
                experiment_id, data['variant'], data['metrics']
            )

            if success:
                return jsonify({'message': 'Observation recorded successfully'})
            else:
                return jsonify({'error': 'Failed to record observation'}), 400

        @self.app.route('/api/experiments/<int:experiment_id>/analyze', methods=['GET'])
        def analyze_experiment(experiment_id):
            result = self.experiment_manager.analyze_experiment(experiment_id)
            return jsonify(result)

        @self.app.route('/api/experiments/<int:experiment_id>', methods=['GET'])
        def get_experiment_status(experiment_id):
            status = self.experiment_manager.get_experiment_status(experiment_id)
            if 'error' in status:
                return jsonify(status), 404
            return jsonify(status)

        @self.app.route('/api/experiments/<int:experiment_id>/deploy', methods=['POST'])
        def deploy_experiment(experiment_id):
            data = request.get_json()
            winner_variant = data.get('winner_variant')

            if not winner_variant:
                return jsonify({'error': 'winner_variant is required'}), 400

            steps = data.get('rollout_steps', [0.1, 0.25, 0.5, 1.0])
            monitoring_periods = data.get('monitoring_periods', 24)

            success = self.deployment_manager.gradual_rollout(
                experiment_id, winner_variant, steps, monitoring_periods
            )

            if success:
                return jsonify({'message': 'Deployment completed successfully'})
            else:
                return jsonify({'error': 'Deployment failed'}), 500

        @self.app.route('/api/experiments/<int:experiment_id>/rollback', methods=['POST'])
        def rollback_experiment(experiment_id):
            success = self.deployment_manager.emergency_rollback(experiment_id)
            if success:
                return jsonify({'message': 'Rollback completed successfully'})
            else:
                return jsonify({'error': 'Rollback failed'}), 500

        @self.app.route('/api/experiments/<int:experiment_id>/deployments', methods=['GET'])
        def get_deployment_history(experiment_id):
            deployments = self.deployment_manager.get_deployment_status(experiment_id)
            return jsonify({'deployments': deployments})

        @self.app.route('/api/statistics/sample-size', methods=['POST'])
        def calculate_sample_size():
            data = request.get_json()
            effect_size = data.get('effect_size', self.config.DEFAULT_MINIMUM_DETECTABLE_EFFECT)
            std_dev = data.get('std_dev')

            sample_size = self.stats_analyzer.calculate_sample_size(effect_size, std_dev)
            return jsonify({
                'required_sample_size': sample_size,
                'effect_size': effect_size,
                'power': self.stats_analyzer.power,
                'significance_level': self.stats_analyzer.significance_level
            })

        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
            })

    def run(self, host: str = None, port: int = None, debug: bool = False):
        """Run the API server"""
        host = host or self.config.API_HOST
        port = port or self.config.API_PORT

        logger.info(f"Starting A/B Testing API on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

# For running the API directly
if __name__ == '__main__':
    config = Config()
    api = ABTestingAPI(config)
    api.run()