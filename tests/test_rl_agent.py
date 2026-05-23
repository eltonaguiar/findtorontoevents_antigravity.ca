"""Test RL trading environment and PPO agent."""
import sys
import numpy as np
import pytest

sys.path.insert(0, '.')


def test_env_reset():
    """Environment should reset to initial state."""
    from rl_agent.trading_env import CryptoTradingEnv

    prices = 60000 * np.exp(np.cumsum(np.random.normal(0, 0.02, 100)))
    env = CryptoTradingEnv(prices)
    obs = env.reset()
    assert obs.shape == (6,)
    assert not env.done


def test_env_step():
    """Environment should step and return reward."""
    from rl_agent.trading_env import CryptoTradingEnv

    prices = 60000 * np.exp(np.cumsum(np.random.normal(0, 0.02, 100)))
    env = CryptoTradingEnv(prices)
    env.reset()

    obs, reward, done, info = env.step(1)  # BUY
    assert obs.shape == (6,)
    assert isinstance(reward, float)
    assert "equity" in info


def test_ppo_agent_act():
    """PPO agent should select valid actions."""
    from rl_agent.ppo_agent import SimplePPOAgent

    agent = SimplePPOAgent()
    obs = np.random.randn(6).astype(np.float32)

    action, log_prob, value = agent.act(obs)
    assert action in (0, 1, 2)
    assert isinstance(log_prob, float)
    assert isinstance(value, float)


def test_train_completes():
    """Training should complete without errors."""
    from rl_agent.train import train, generate_synthetic_prices

    prices = generate_synthetic_prices(500)
    _agent, results = train(prices, n_episodes=5, sharpe_penalty=0.1)

    assert results["n_episodes"] == 5
    assert "best_sharpe" in results
    assert len(results["history"]) == 5


def test_episode_stats():
    """Episode should produce valid stats."""
    from rl_agent.trading_env import CryptoTradingEnv

    np.random.seed(42)
    prices = 60000 * np.exp(np.cumsum(np.random.normal(0, 0.02, 200)))
    env = CryptoTradingEnv(prices)
    env.reset()

    # Run through the episode
    while not env.done:
        action = np.random.choice(3)
        env.step(action)

    stats = env.get_episode_stats()
    assert "total_return" in stats
    assert "sharpe" in stats
    assert "max_drawdown" in stats
    assert stats["max_drawdown"] >= 0
