from flask import Flask, render_template, request, jsonify
import json
import logging

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

class ABTestingDashboard:
    """Web dashboard for A/B Testing Agent"""

    def __init__(self, config: Config):
        self.config = config
        self.app = Flask(__name__,
                        template_folder='templates',
                        static_folder='static')

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
        """Setup dashboard routes"""

        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')

        @self.app.route('/experiment/<int:experiment_id>')
        def experiment_detail(experiment_id):
            experiment = self.experiment_manager.get_experiment_status(experiment_id)
            if 'error' in experiment:
                return f"Error: {experiment['error']}", 404

            analysis = experiment.get('analysis', {})

            return render_template('experiment_detail.html',
                                 experiment=experiment,
                                 analysis=analysis)

    def run(self, host: str = None, port: int = None, debug: bool = False):
        """Run the dashboard server"""
        host = host or self.config.API_HOST
        port = (port or self.config.API_PORT) + 1  # Different port from API

        logger.info(f"Starting A/B Testing Dashboard on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

# For running the dashboard directly
if __name__ == '__main__':
    config = Config()
    dashboard = ABTestingDashboard(config)
    dashboard.run()