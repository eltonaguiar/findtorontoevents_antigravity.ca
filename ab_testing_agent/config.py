import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///ab_testing.db')

    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 5000))

    # Experiment settings
    DEFAULT_SIGNIFICANCE_LEVEL = 0.05
    DEFAULT_POWER = 0.80
    DEFAULT_MINIMUM_DETECTABLE_EFFECT = 0.01

    # Monitoring
    ALERT_EMAIL = os.getenv('ALERT_EMAIL')
    SMTP_SERVER = os.getenv('SMTP_SERVER')

    # Deployment
    PRODUCTION_URL = os.getenv('PRODUCTION_URL')
    STAGING_URL = os.getenv('STAGING_URL')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'ab_testing.log')