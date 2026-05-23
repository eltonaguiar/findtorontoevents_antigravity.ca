class PPOAgent:
    '''Mock PPO agent for testing purposes.'''
    def __init__(self):
        pass

    def load(self, model_path):
        # Mock load – in production load actual torch model
        pass

    def act(self, obs):
        # Mock action: always long BTC for testing
        return {"BTC": 1.0}