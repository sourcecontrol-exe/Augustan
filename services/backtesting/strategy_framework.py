# ==============================================================================
# File: strategy_framework.py
# Description: Flexible strategy framework for combining indicators and rules
# ==============================================================================

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import json

from backtesting.indicators import TechnicalIndicators, CustomIndicators


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ConditionOperator(Enum):
    AND = "AND"
    OR = "OR"


@dataclass
class StrategyCondition:
    """Represents a single condition in a strategy"""
    indicator: str
    column: str
    operator: str  # '>', '<', '>=', '<=', '==', '!=', 'cross_above', 'cross_below'
    value: Union[float, str]  # Can be a number or another column name
    description: str = ""


@dataclass
class StrategyRule:
    """Represents a rule with multiple conditions"""
    conditions: List[StrategyCondition]
    condition_operator: ConditionOperator = ConditionOperator.AND
    signal: SignalType = SignalType.HOLD
    description: str = ""


@dataclass
class StrategyConfig:
    """Complete strategy configuration"""
    name: str
    description: str
    indicators: List[Dict[str, Any]]
    entry_rules: List[StrategyRule]
    exit_rules: List[StrategyRule]
    risk_management: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.indicators_lib = TechnicalIndicators()
        self.custom_indicators = CustomIndicators()
        self._prepared_data = None
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data by calculating all required indicators"""
        if self._prepared_data is not None and len(self._prepared_data) == len(df):
            return self._prepared_data
        
        result_df = df.copy()
        
        # Calculate all indicators specified in config
        for indicator_config in self.config.indicators:
            name = indicator_config['name']
            params = indicator_config.get('params', {})
            result_df = self.indicators_lib.calculate_indicator(result_df, name, params)
        
        self._prepared_data = result_df
        return result_df
    
    def evaluate_condition(self, df: pd.DataFrame, condition: StrategyCondition, index: int) -> bool:
        """Evaluate a single condition at a specific index"""
        try:
            if index < 0 or index >= len(df):
                return False
            
            row = df.iloc[index]
            
            if condition.column not in df.columns:
                return False
            
            left_value = row[condition.column]
            
            # Handle different value types
            if isinstance(condition.value, str) and condition.value in df.columns:
                right_value = row[condition.value]
            else:
                right_value = float(condition.value)
            
            # Handle NaN values
            if pd.isna(left_value) or pd.isna(right_value):
                return False
            
            # Evaluate based on operator
            if condition.operator == '>':
                return left_value > right_value
            elif condition.operator == '<':
                return left_value < right_value
            elif condition.operator == '>=':
                return left_value >= right_value
            elif condition.operator == '<=':
                return left_value <= right_value
            elif condition.operator == '==':
                return abs(left_value - right_value) < 1e-10
            elif condition.operator == '!=':
                return abs(left_value - right_value) >= 1e-10
            elif condition.operator == 'cross_above':
                if index == 0:
                    return False
                prev_left = df.iloc[index - 1][condition.column]
                if isinstance(condition.value, str) and condition.value in df.columns:
                    prev_right = df.iloc[index - 1][condition.value]
                else:
                    prev_right = right_value
                return prev_left <= prev_right and left_value > right_value
            elif condition.operator == 'cross_below':
                if index == 0:
                    return False
                prev_left = df.iloc[index - 1][condition.column]
                if isinstance(condition.value, str) and condition.value in df.columns:
                    prev_right = df.iloc[index - 1][condition.value]
                else:
                    prev_right = right_value
                return prev_left >= prev_right and left_value < right_value
            
            return False
            
        except Exception:
            return False
    
    def evaluate_rule(self, df: pd.DataFrame, rule: StrategyRule, index: int) -> bool:
        """Evaluate a complete rule at a specific index"""
        if not rule.conditions:
            return False
        
        condition_results = []
        for condition in rule.conditions:
            result = self.evaluate_condition(df, condition, index)
            condition_results.append(result)
        
        if rule.condition_operator == ConditionOperator.AND:
            return all(condition_results)
        else:  # OR
            return any(condition_results)
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, index: int) -> SignalType:
        """Generate trading signal for a specific index"""
        pass
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate signals for entire dataframe"""
        prepared_df = self.prepare_data(df)
        signals = []
        
        for i in range(len(prepared_df)):
            signal = self.generate_signal(prepared_df, i)
            signals.append(signal.value)
        
        return pd.Series(signals, index=df.index, name='signal')


class RuleBasedStrategy(BaseStrategy):
    """Strategy that uses rule-based logic for signal generation"""
    
    def generate_signal(self, df: pd.DataFrame, index: int) -> SignalType:
        """Generate signal based on entry and exit rules"""
        # Check entry rules first
        for rule in self.config.entry_rules:
            if self.evaluate_rule(df, rule, index):
                return rule.signal
        
        # Check exit rules
        for rule in self.config.exit_rules:
            if self.evaluate_rule(df, rule, index):
                return rule.signal
        
        return SignalType.HOLD


class MLStrategy(BaseStrategy):
    """Strategy that uses machine learning models"""
    
    def __init__(self, config: StrategyConfig, model: Optional[Any] = None):
        super().__init__(config)
        self.model = model
        self.feature_columns = []
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for ML model"""
        prepared_df = self.prepare_data(df)
        
        # Extract feature columns (all indicator columns)
        base_columns = ['open', 'high', 'low', 'close', 'volume']
        self.feature_columns = [col for col in prepared_df.columns if col not in base_columns]
        
        return prepared_df[self.feature_columns].fillna(0)
    
    def generate_signal(self, df: pd.DataFrame, index: int) -> SignalType:
        """Generate signal using ML model"""
        if self.model is None:
            return SignalType.HOLD
        
        features = self.prepare_features(df)
        
        if index >= len(features):
            return SignalType.HOLD
        
        try:
            # Get features for current index
            current_features = features.iloc[index:index+1]
            
            # Predict using model
            prediction = self.model.predict(current_features)[0]
            
            # Convert prediction to signal
            if prediction > 0.6:
                return SignalType.BUY
            elif prediction < 0.4:
                return SignalType.SELL
            else:
                return SignalType.HOLD
                
        except Exception:
            return SignalType.HOLD


class StrategyFactory:
    """Factory for creating different types of strategies"""
    
    @staticmethod
    def create_rsi_macd_strategy() -> StrategyConfig:
        """Create the classic RSI + MACD strategy"""
        return StrategyConfig(
            name="RSI_MACD_Strategy",
            description="Classic RSI oversold/overbought with MACD confirmation",
            indicators=[
                {"name": "rsi", "params": {"length": 14}},
                {"name": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}}
            ],
            entry_rules=[
                StrategyRule(
                    conditions=[
                        StrategyCondition("rsi", "RSI_14", "<", 30, "RSI oversold"),
                        StrategyCondition("macd", "MACD_12_26_9", "cross_above", "MACDs_12_26_9", "MACD bullish crossover")
                    ],
                    signal=SignalType.BUY,
                    description="Buy when RSI oversold and MACD crosses above signal"
                ),
                StrategyRule(
                    conditions=[
                        StrategyCondition("rsi", "RSI_14", ">", 70, "RSI overbought"),
                        StrategyCondition("macd", "MACD_12_26_9", "cross_below", "MACDs_12_26_9", "MACD bearish crossover")
                    ],
                    signal=SignalType.SELL,
                    description="Sell when RSI overbought and MACD crosses below signal"
                )
            ],
            exit_rules=[]
        )
    
    @staticmethod
    def create_bollinger_rsi_strategy() -> StrategyConfig:
        """Create Bollinger Bands + RSI strategy"""
        return StrategyConfig(
            name="Bollinger_RSI_Strategy",
            description="Bollinger Bands breakout with RSI confirmation",
            indicators=[
                {"name": "bb", "params": {"length": 20, "std": 2}},
                {"name": "rsi", "params": {"length": 14}}
            ],
            entry_rules=[
                StrategyRule(
                    conditions=[
                        StrategyCondition("price", "close", "<", "BBL_20_2.0", "Price below lower BB"),
                        StrategyCondition("rsi", "RSI_14", "<", 35, "RSI oversold confirmation")
                    ],
                    signal=SignalType.BUY,
                    description="Buy when price below lower BB and RSI oversold"
                ),
                StrategyRule(
                    conditions=[
                        StrategyCondition("price", "close", ">", "BBU_20_2.0", "Price above upper BB"),
                        StrategyCondition("rsi", "RSI_14", ">", 65, "RSI overbought confirmation")
                    ],
                    signal=SignalType.SELL,
                    description="Sell when price above upper BB and RSI overbought"
                )
            ],
            exit_rules=[]
        )
    
    @staticmethod
    def create_multi_timeframe_strategy() -> StrategyConfig:
        """Create multi-timeframe strategy"""
        return StrategyConfig(
            name="Multi_Timeframe_Strategy",
            description="Multiple timeframe analysis with trend confirmation",
            indicators=[
                {"name": "ema", "params": {"length": 20}},
                {"name": "ema", "params": {"length": 50}},
                {"name": "rsi", "params": {"length": 14}},
                {"name": "macd", "params": {"fast": 12, "slow": 26, "signal": 9}},
                {"name": "adx", "params": {"length": 14}}
            ],
            entry_rules=[
                StrategyRule(
                    conditions=[
                        StrategyCondition("trend", "EMA_20", ">", "EMA_50", "Short EMA above long EMA"),
                        StrategyCondition("momentum", "RSI_14", ">", 50, "RSI above midline"),
                        StrategyCondition("trend_strength", "ADX_14", ">", 25, "Strong trend"),
                        StrategyCondition("macd", "MACD_12_26_9", ">", "MACDs_12_26_9", "MACD above signal")
                    ],
                    signal=SignalType.BUY,
                    description="Buy in strong uptrend with momentum"
                ),
                StrategyRule(
                    conditions=[
                        StrategyCondition("trend", "EMA_20", "<", "EMA_50", "Short EMA below long EMA"),
                        StrategyCondition("momentum", "RSI_14", "<", 50, "RSI below midline"),
                        StrategyCondition("trend_strength", "ADX_14", ">", 25, "Strong trend"),
                        StrategyCondition("macd", "MACD_12_26_9", "<", "MACDs_12_26_9", "MACD below signal")
                    ],
                    signal=SignalType.SELL,
                    description="Sell in strong downtrend with momentum"
                )
            ],
            exit_rules=[]
        )
    
    @staticmethod
    def from_json(json_str: str) -> StrategyConfig:
        """Create strategy from JSON configuration"""
        data = json.loads(json_str)
        
        # Convert conditions
        def parse_conditions(conditions_data):
            return [
                StrategyCondition(
                    indicator=c['indicator'],
                    column=c['column'],
                    operator=c['operator'],
                    value=c['value'],
                    description=c.get('description', '')
                ) for c in conditions_data
            ]
        
        # Convert rules
        def parse_rules(rules_data):
            return [
                StrategyRule(
                    conditions=parse_conditions(r['conditions']),
                    condition_operator=ConditionOperator(r.get('condition_operator', 'AND')),
                    signal=SignalType(r['signal']),
                    description=r.get('description', '')
                ) for r in rules_data
            ]
        
        return StrategyConfig(
            name=data['name'],
            description=data['description'],
            indicators=data['indicators'],
            entry_rules=parse_rules(data['entry_rules']),
            exit_rules=parse_rules(data['exit_rules']),
            risk_management=data.get('risk_management', {}),
            parameters=data.get('parameters', {})
        )


class StrategyOptimizer:
    """Optimize strategy parameters using various methods"""
    
    def __init__(self, base_strategy_config: StrategyConfig):
        self.base_config = base_strategy_config
        self.optimization_results = []
    
    def grid_search(self, df: pd.DataFrame, parameter_grid: Dict[str, List[Any]], 
                   metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """Perform grid search optimization"""
        from itertools import product
        
        best_params = None
        best_score = float('-inf')
        
        # Generate all parameter combinations
        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())
        
        for combination in product(*param_values):
            params = dict(zip(param_names, combination))
            
            # Create modified strategy config
            modified_config = self._apply_parameters(self.base_config, params)
            
            # Test strategy
            strategy = RuleBasedStrategy(modified_config)
            signals = strategy.generate_signals(df)
            
            # Calculate performance metric
            score = self._calculate_metric(df, signals, metric)
            
            if score > best_score:
                best_score = score
                best_params = params
            
            self.optimization_results.append({
                'parameters': params,
                'score': score,
                'metric': metric
            })
        
        return {
            'best_parameters': best_params,
            'best_score': best_score,
            'all_results': self.optimization_results
        }
    
    def _apply_parameters(self, config: StrategyConfig, params: Dict[str, Any]) -> StrategyConfig:
        """Apply parameter modifications to strategy config"""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated parameter mapping
        modified_config = config
        # Apply parameter modifications here
        return modified_config
    
    def _calculate_metric(self, df: pd.DataFrame, signals: pd.Series, metric: str) -> float:
        """Calculate performance metric for optimization"""
        # Simplified metric calculation
        # In practice, you'd use the full backtesting engine
        if metric == 'sharpe_ratio':
            returns = df['close'].pct_change()
            strategy_returns = returns * signals.shift(1).map({'BUY': 1, 'SELL': -1, 'HOLD': 0}).fillna(0)
            return strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() > 0 else 0
        
        return 0
