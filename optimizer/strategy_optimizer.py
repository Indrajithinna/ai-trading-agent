"""
Strategy Optimizer AI (Module 16)
===================================
Uses historical data to tune strategy parameters.
Methods: Grid Search, Random Search, Genetic Algorithm.
Runs weekly optimization.
"""

import random
import json
import os
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from copy import deepcopy

import numpy as np

from ai_trading_agent.config import OptimizerConfig
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("StrategyOptimizer")


class StrategyOptimizer:
    """
    Auto-tunes strategy parameters using optimization algorithms.
    
    Methods:
    1. Grid Search: Exhaustive search over parameter grid
    2. Random Search: Random sampling of parameter space
    3. Genetic Algorithm: Evolutionary optimization
    
    Optimization Target: Maximize Sharpe-adjusted returns
    """
    
    def __init__(self, config: OptimizerConfig):
        self.config = config
        self._optimization_history: List[Dict] = []
        self._best_params: Dict[str, Dict] = {}
        
        self._data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self._data_dir, exist_ok=True)
        
        logger.info("StrategyOptimizer initialized")
    
    def optimize(self, strategy_name: str, 
                 param_space: Dict[str, List],
                 evaluate_fn: Callable,
                 method: str = "random_search") -> Dict[str, Any]:
        """
        Optimize strategy parameters.
        
        Args:
            strategy_name: Name of the strategy to optimize
            param_space: Dictionary of parameter names to list of possible values
            evaluate_fn: Function that takes params dict and returns fitness score
            method: Optimization method ("grid_search", "random_search", "genetic_algorithm")
            
        Returns:
            Best parameters found and optimization metrics
        """
        logger.info(f"🔧 Starting {method} optimization for {strategy_name}")
        
        if method == "grid_search":
            result = self._grid_search(param_space, evaluate_fn)
        elif method == "random_search":
            result = self._random_search(param_space, evaluate_fn)
        elif method == "genetic_algorithm":
            result = self._genetic_algorithm(param_space, evaluate_fn)
        else:
            logger.warning(f"Unknown method: {method}. Using random_search.")
            result = self._random_search(param_space, evaluate_fn)
        
        result['strategy'] = strategy_name
        result['method'] = method
        result['timestamp'] = datetime.now().isoformat()
        
        self._optimization_history.append(result)
        self._best_params[strategy_name] = result.get('best_params', {})
        
        logger.info(
            f"✅ {strategy_name} optimization complete | "
            f"Best Score: {result.get('best_score', 0):.4f} | "
            f"Evaluations: {result.get('evaluations', 0)}"
        )
        
        self._save_results()
        
        return result
    
    def _grid_search(self, param_space: Dict[str, List], 
                     evaluate_fn: Callable) -> Dict[str, Any]:
        """Exhaustive grid search over parameter combinations."""
        from itertools import product
        
        keys = list(param_space.keys())
        values = list(param_space.values())
        
        best_score = float('-inf')
        best_params = {}
        evaluations = 0
        all_results = []
        
        for combo in product(*values):
            params = dict(zip(keys, combo))
            
            try:
                score = evaluate_fn(params)
                evaluations += 1
                
                all_results.append({'params': params, 'score': score})
                
                if score > best_score:
                    best_score = score
                    best_params = params.copy()
                    
            except Exception as e:
                logger.error(f"Evaluation error: {e}")
        
        return {
            'best_params': best_params,
            'best_score': round(best_score, 4),
            'evaluations': evaluations,
            'top_results': sorted(all_results, key=lambda x: x['score'], reverse=True)[:5]
        }
    
    def _random_search(self, param_space: Dict[str, List], 
                       evaluate_fn: Callable,
                       n_iterations: int = 100) -> Dict[str, Any]:
        """Random sampling of parameter space."""
        best_score = float('-inf')
        best_params = {}
        evaluations = 0
        all_results = []
        
        for _ in range(n_iterations):
            params = {k: random.choice(v) for k, v in param_space.items()}
            
            try:
                score = evaluate_fn(params)
                evaluations += 1
                
                all_results.append({'params': params, 'score': score})
                
                if score > best_score:
                    best_score = score
                    best_params = params.copy()
                    
            except Exception as e:
                logger.error(f"Evaluation error: {e}")
        
        return {
            'best_params': best_params,
            'best_score': round(best_score, 4),
            'evaluations': evaluations,
            'top_results': sorted(all_results, key=lambda x: x['score'], reverse=True)[:5]
        }
    
    def _genetic_algorithm(self, param_space: Dict[str, List], 
                           evaluate_fn: Callable) -> Dict[str, Any]:
        """Genetic algorithm optimization."""
        pop_size = self.config.population_size
        generations = self.config.generations
        mutation_rate = self.config.mutation_rate
        crossover_rate = self.config.crossover_rate
        
        keys = list(param_space.keys())
        
        # Initialize population
        population = []
        for _ in range(pop_size):
            individual = {k: random.choice(v) for k, v in param_space.items()}
            population.append(individual)
        
        best_score = float('-inf')
        best_params = {}
        evaluations = 0
        generation_scores = []
        
        for gen in range(generations):
            # Evaluate fitness
            fitness = []
            for individual in population:
                try:
                    score = evaluate_fn(individual)
                    fitness.append(score)
                    evaluations += 1
                    
                    if score > best_score:
                        best_score = score
                        best_params = individual.copy()
                except:
                    fitness.append(float('-inf'))
            
            generation_scores.append({
                'generation': gen,
                'best': max(fitness),
                'avg': np.mean([f for f in fitness if f > float('-inf')]),
            })
            
            # Selection (tournament)
            new_population = []
            
            # Elitism - keep top 10%
            elite_count = max(1, pop_size // 10)
            elite_indices = np.argsort(fitness)[-elite_count:]
            for idx in elite_indices:
                new_population.append(population[idx].copy())
            
            # Fill rest with crossover and mutation
            while len(new_population) < pop_size:
                # Tournament selection
                parent1 = self._tournament_select(population, fitness, 3)
                parent2 = self._tournament_select(population, fitness, 3)
                
                # Crossover
                if random.random() < crossover_rate:
                    child = self._crossover(parent1, parent2, keys)
                else:
                    child = parent1.copy()
                
                # Mutation
                child = self._mutate(child, param_space, mutation_rate)
                
                new_population.append(child)
            
            population = new_population[:pop_size]
        
        return {
            'best_params': best_params,
            'best_score': round(best_score, 4),
            'evaluations': evaluations,
            'generations': generations,
            'generation_progress': generation_scores[-10:]  # Last 10 generations
        }
    
    def _tournament_select(self, population: List[Dict], 
                           fitness: List[float], k: int = 3) -> Dict:
        """Tournament selection."""
        indices = random.sample(range(len(population)), min(k, len(population)))
        best_idx = max(indices, key=lambda i: fitness[i])
        return population[best_idx].copy()
    
    def _crossover(self, parent1: Dict, parent2: Dict, keys: List[str]) -> Dict:
        """Single-point crossover."""
        point = random.randint(1, len(keys) - 1)
        child = {}
        for i, key in enumerate(keys):
            if i < point:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        return child
    
    def _mutate(self, individual: Dict, param_space: Dict[str, List], 
                rate: float) -> Dict:
        """Mutate individual parameters."""
        for key in individual:
            if random.random() < rate and key in param_space:
                individual[key] = random.choice(param_space[key])
        return individual
    
    def get_default_param_spaces(self) -> Dict[str, Dict[str, List]]:
        """Get default optimization parameter spaces for each strategy."""
        return {
            "VWAP_BREAKOUT": {
                "rsi_buy_threshold": [55, 58, 60, 62, 65],
                "rsi_sell_threshold": [35, 38, 40, 42, 45],
                "volume_spike_multiplier": [1.2, 1.3, 1.5, 1.8, 2.0]
            },
            "EMA_MOMENTUM": {
                "ema_fast": [5, 7, 9, 12],
                "ema_slow": [15, 18, 21, 25, 30]
            },
            "ORB_BREAKOUT": {
                "breakout_buffer_pct": [0.05, 0.1, 0.15, 0.2, 0.25]
            }
        }
    
    def _save_results(self):
        """Save optimization results to disk."""
        path = os.path.join(self._data_dir, "optimization_results.json")
        try:
            with open(path, 'w') as f:
                json.dump({
                    'history': self._optimization_history[-20:],
                    'best_params': self._best_params,
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving optimization results: {e}")
    
    def get_best_params(self, strategy_name: str) -> Dict:
        """Get best optimized parameters for a strategy."""
        return self._best_params.get(strategy_name, {})
