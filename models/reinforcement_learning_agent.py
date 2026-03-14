"""
Reinforcement Learning Trading Agent (Module 8)
=================================================
RL policy for trading decisions.
States: market indicators, volatility, trend strength, position status
Actions: BUY_CALL, BUY_PUT, HOLD
Rewards: profit, risk-adjusted returns
"""

import os
import pickle
import random
from collections import deque
from typing import Dict, List, Tuple, Optional, Any

import numpy as np

from ai_trading_agent.config import RLConfig
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("RLAgent")


class ReplayMemory:
    """Experience replay buffer for the RL agent."""
    
    def __init__(self, capacity: int):
        self.memory = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size: int):
        batch = random.sample(self.memory, min(batch_size, len(self.memory)))
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones)
        )
    
    def __len__(self):
        return len(self.memory)


class RLTradingAgent:
    """
    Reinforcement Learning Trading Agent using Deep Q-Network (DQN).
    
    State Space:
    - RSI, MACD, EMA difference, VWAP difference
    - ATR, Volume ratio, Trend strength, Volatility
    - Position status (0=flat, 1=long call, 2=long put)
    - Unrealized P&L
    
    Action Space:
    - 0: BUY_CALL
    - 1: BUY_PUT  
    - 2: HOLD
    
    Reward:
    - Profit from trades
    - Risk-adjusted returns (Sharpe-like)
    - Penalties for excessive trading
    """
    
    def __init__(self, config: RLConfig):
        self.config = config
        self.state_size = len(config.state_features)
        self.action_size = len(config.actions)
        
        # Q-table (simple tabular approach — works for paper trading)
        self.q_table: Dict[str, np.ndarray] = {}
        
        # Exploration
        self.epsilon = config.epsilon_start
        self.epsilon_min = config.epsilon_end
        self.epsilon_decay = config.epsilon_decay
        
        # Learning
        self.learning_rate = config.learning_rate
        self.gamma = config.gamma
        
        # Memory
        self.memory = ReplayMemory(config.memory_size)
        
        # Training stats
        self.total_episodes = 0
        self.total_steps = 0
        self.total_reward = 0.0
        self.episode_rewards: List[float] = []
        
        # Neural network (optional, for more complex learning)
        self._nn_model = None
        self._use_nn = False
        
        logger.info(f"RLTradingAgent initialized | States: {self.state_size} | Actions: {self.action_size}")
    
    def get_state_key(self, state: np.ndarray) -> str:
        """Discretize state for Q-table lookup."""
        # Bin continuous values into discrete buckets
        bins = 10
        discretized = np.clip(
            np.floor(state * bins).astype(int), -bins * 5, bins * 5
        )
        return str(tuple(discretized))
    
    def normalize_state(self, raw_state: Dict[str, float]) -> np.ndarray:
        """Normalize raw state dictionary to a state vector."""
        state = np.zeros(self.state_size)
        
        for i, feature in enumerate(self.config.state_features):
            if i >= self.state_size:
                break
            
            value = raw_state.get(feature, 0.0)
            
            # Normalize different features to [-1, 1] or [0, 1]
            if feature == 'rsi':
                state[i] = (value - 50) / 50  # [-1, 1]
            elif feature == 'macd':
                state[i] = np.clip(value / 5, -1, 1)
            elif feature in ('ema_diff', 'vwap_diff'):
                state[i] = np.clip(value / 100, -1, 1)
            elif feature == 'atr':
                state[i] = np.clip(value / 200, 0, 1)
            elif feature == 'volume_ratio':
                state[i] = np.clip(value / 3, 0, 1)
            elif feature == 'trend_strength':
                state[i] = np.clip(value / 100, 0, 1)
            elif feature == 'volatility':
                state[i] = np.clip(value / 100, 0, 1)
            elif feature == 'position_status':
                state[i] = value  # 0, 1, or 2
            elif feature == 'unrealized_pnl':
                state[i] = np.clip(value / 1000, -1, 1)
            else:
                state[i] = np.clip(value, -1, 1)
        
        return state
    
    def select_action(self, state: np.ndarray) -> int:
        """Select action using epsilon-greedy policy."""
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        
        state_key = self.get_state_key(state)
        
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_size)
        
        return int(np.argmax(self.q_table[state_key]))
    
    def get_action_name(self, action: int) -> str:
        """Map action index to action name."""
        if action < len(self.config.actions):
            return self.config.actions[action]
        return "HOLD"
    
    def learn(self, state: np.ndarray, action: int, reward: float, 
              next_state: np.ndarray, done: bool):
        """Update Q-values using Q-learning update rule."""
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)
        
        # Initialize Q-values if needed
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_size)
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(self.action_size)
        
        # Q-learning update
        current_q = self.q_table[state_key][action]
        
        if done:
            target_q = reward
        else:
            target_q = reward + self.gamma * np.max(self.q_table[next_state_key])
        
        self.q_table[state_key][action] += self.learning_rate * (target_q - current_q)
        
        # Store experience
        self.memory.push(state, action, reward, next_state, done)
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        self.total_steps += 1
    
    def calculate_reward(self, pnl: float, risk_taken: float = 1.0,
                        trade_result: str = "open") -> float:
        """
        Calculate reward for a trading action.
        
        Rewards:
        - Profit: positive reward scaled by P&L
        - Risk-adjusted: penalize excessive risk
        - Win: bonus for profitable trades
        - Loss: penalty for losing trades
        - Hold penalty: small negative for excessive holding
        """
        reward = 0.0
        
        if trade_result == "win":
            reward = pnl / 100  # Scale profit
            reward += 0.5  # Win bonus
        elif trade_result == "loss":
            reward = pnl / 100  # Negative value
            reward -= 0.3  # Loss penalty
        elif trade_result == "hold":
            reward = -0.01  # Small penalty for holding
        elif trade_result == "open":
            reward = pnl / 200  # Partial reward for unrealized P&L
        
        # Risk adjustment
        if risk_taken > 2.0:
            reward -= 0.2  # Excessive risk penalty
        
        return round(reward, 4)
    
    def train_episode(self, states: List[np.ndarray], actions: List[int],
                     rewards: List[float]) -> float:
        """Train on a complete episode of states, actions, and rewards."""
        total_reward = 0.0
        
        for i in range(len(states) - 1):
            done = (i == len(states) - 2)
            self.learn(states[i], actions[i], rewards[i], states[i + 1], done)
            total_reward += rewards[i]
        
        self.total_episodes += 1
        self.total_reward += total_reward
        self.episode_rewards.append(total_reward)
        
        if len(self.episode_rewards) > 1000:
            self.episode_rewards = self.episode_rewards[-1000:]
        
        return total_reward
    
    def predict(self, raw_state: Dict[str, float]) -> Dict[str, Any]:
        """
        Get RL agent's trading recommendation.
        
        Args:
            raw_state: Dictionary of current market state features
            
        Returns:
            Dictionary with action, confidence, and details
        """
        state = self.normalize_state(raw_state)
        action = self.select_action(state)
        action_name = self.get_action_name(action)
        
        state_key = self.get_state_key(state)
        q_values = self.q_table.get(state_key, np.zeros(self.action_size))
        
        # Calculate confidence from Q-values
        q_range = np.max(q_values) - np.min(q_values)
        confidence = min(100, (q_range / (abs(np.mean(q_values)) + 1e-8)) * 50) \
            if q_range > 0 else 30
        
        return {
            "action": action_name,
            "action_index": action,
            "confidence": round(confidence, 2),
            "q_values": {
                self.config.actions[i]: round(float(q), 4) 
                for i, q in enumerate(q_values)
            },
            "epsilon": round(self.epsilon, 4),
            "total_episodes": self.total_episodes,
            "total_steps": self.total_steps
        }
    
    def save(self, path: str = "models/saved/rl_agent.pkl"):
        """Save RL agent state."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            'q_table': dict(self.q_table),
            'epsilon': self.epsilon,
            'total_episodes': self.total_episodes,
            'total_steps': self.total_steps,
            'total_reward': self.total_reward,
            'episode_rewards': self.episode_rewards[-100:]
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)
        logger.info(f"💾 RL Agent saved | Episodes: {self.total_episodes}")
    
    def load(self, path: str = "models/saved/rl_agent.pkl") -> bool:
        """Load RL agent state."""
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    state = pickle.load(f)
                self.q_table = state['q_table']
                self.epsilon = state['epsilon']
                self.total_episodes = state['total_episodes']
                self.total_steps = state['total_steps']
                self.total_reward = state['total_reward']
                self.episode_rewards = state.get('episode_rewards', [])
                logger.info(f"📂 RL Agent loaded | Episodes: {self.total_episodes}")
                return True
        except Exception as e:
            logger.error(f"Error loading RL agent: {e}")
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get training statistics."""
        recent = self.episode_rewards[-100:] if self.episode_rewards else [0]
        return {
            "total_episodes": self.total_episodes,
            "total_steps": self.total_steps,
            "total_reward": round(self.total_reward, 2),
            "avg_reward_100": round(np.mean(recent), 4),
            "epsilon": round(self.epsilon, 4),
            "q_table_size": len(self.q_table),
            "memory_size": len(self.memory)
        }
