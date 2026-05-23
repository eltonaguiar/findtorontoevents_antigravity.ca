from ENGINE_KEY_ENVS import ENGINE_KEY_ENVS

def load_dotenv(env_path: str) -> dict:
    """Load .env file, overriding only empty/whitespace env vars."""
    applied = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            existing = __import__('os').environ.get(key)
            if existing is None or existing.strip() == '':
                __import__('os').environ[key] = value
                applied[key] = value
    return applied

def load_config(config_path: str, ts: str = None) -> dict:
    """Load and parse YAML config with variable substitution."""
    import yaml
    import os
    
    if ts is None:
        from datetime import datetime
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Simple variable substitution
    def substitute_vars(obj):
        if isinstance(obj, str):
            obj = obj.replace('${TS}', ts)
            # Add other substitutions as needed
            return obj
        elif isinstance(obj, dict):
            return {k: substitute_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [substitute_vars(item) for item in obj]
        else:
            return obj
    
    return substitute_vars(config)