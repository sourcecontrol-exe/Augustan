"""
Strategy Factory and Registry - Dynamic strategy loading and creation.

Provides:
- StrategyRegistry: Register strategy classes
- StrategyFactory: Create strategy instances from configuration
- Plugin-based architecture for extensibility
"""
from typing import Dict, Type, Optional, Any, List
from loguru import logger
from dataclasses import dataclass

from .base_strategy import BaseStrategy
from ..core.models import StrategyType


@dataclass
class StrategyConfig:
    """Configuration for a strategy."""
    strategy_type: StrategyType
    enabled: bool = True
    priority: int = 1
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class StrategyRegistry:
    """
    Registry for strategy classes.
    
    Allows dynamic registration and discovery of strategies.
    Supports plugin-based architecture.
    """
    
    _strategies: Dict[StrategyType, Type[BaseStrategy]] = {}
    
    @classmethod
    def register(cls, strategy_type: StrategyType, strategy_class: Type[BaseStrategy]):
        """
        Register a strategy class.
        
        Args:
            strategy_type: Type of strategy
            strategy_class: Strategy class to register
        """
        if strategy_type in cls._strategies:
            logger.warning(f"Overwriting existing strategy: {strategy_type.value}")
        
        cls._strategies[strategy_type] = strategy_class
        logger.info(f"Registered strategy: {strategy_type.value}")
    
    @classmethod
    def unregister(cls, strategy_type: StrategyType):
        """Unregister a strategy."""
        if strategy_type in cls._strategies:
            del cls._strategies[strategy_type]
            logger.info(f"Unregistered strategy: {strategy_type.value}")
    
    @classmethod
    def get(cls, strategy_type: StrategyType) -> Optional[Type[BaseStrategy]]:
        """Get a registered strategy class."""
        return cls._strategies.get(strategy_type)
    
    @classmethod
    def list_registered(cls) -> List[StrategyType]:
        """List all registered strategy types."""
        return list(cls._strategies.keys())
    
    @classmethod
    def is_registered(cls, strategy_type: StrategyType) -> bool:
        """Check if strategy type is registered."""
        return strategy_type in cls._strategies


class StrategyFactory:
    """
    Factory for creating strategy instances.
    
    Creates strategy instances from configuration using the registry.
    Supports dynamic instantiation based on configuration.
    """
    
    @staticmethod
    def create_from_config(config: StrategyConfig) -> Optional[BaseStrategy]:
        """
        Create a strategy instance from configuration.
        
        Args:
            config: Strategy configuration
            
        Returns:
            Strategy instance or None if not enabled or not registered
        """
        if not config.enabled:
            logger.debug(f"Strategy {config.strategy_type.value} is disabled")
            return None
        
        strategy_class = StrategyRegistry.get(config.strategy_type)
        
        if not strategy_class:
            logger.warning(f"Strategy {config.strategy_type.value} not registered")
            return None
        
        try:
            # Create instance with parameters from config
            if config.parameters:
                strategy = strategy_class(**config.parameters)
            else:
                strategy = strategy_class()
            
            logger.info(f"Created strategy instance: {config.strategy_type.value}")
            return strategy
            
        except Exception as e:
            logger.error(f"Error creating strategy {config.strategy_type.value}: {e}")
            return None
    
    @staticmethod
    def create_batch_from_configs(configs: List[StrategyConfig]) -> Dict[StrategyType, BaseStrategy]:
        """
        Create multiple strategy instances from configurations.
        
        Args:
            configs: List of strategy configurations
            
        Returns:
            Dictionary mapping strategy types to instances
        """
        strategies = {}
        
        for config in configs:
            strategy = StrategyFactory.create_from_config(config)
            if strategy:
                strategies[config.strategy_type] = strategy
        
        logger.info(f"Created {len(strategies)} strategies from config")
        return strategies
    
    @staticmethod
    def create_from_config_dict(config_dict: Dict[str, Any]) -> Dict[StrategyType, BaseStrategy]:
        """
        Create strategies from a configuration dictionary.
        
        Args:
            config_dict: Dictionary with strategy configurations
                Example: {
                    "rsi": {
                        "enabled": True,
                        "parameters": {"period": 14}
                    }
                }
        
        Returns:
            Dictionary of strategy instances
        """
        configs = []
        
        for key, value in config_dict.items():
            try:
                # Convert string key to StrategyType
                strategy_type = StrategyType[key.upper()]
                
                config = StrategyConfig(
                    strategy_type=strategy_type,
                    enabled=value.get('enabled', True),
                    priority=value.get('priority', 1),
                    parameters=value.get('parameters', {})
                )
                configs.append(config)
                
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid strategy config: {key} - {e}")
                continue
        
        return StrategyFactory.create_batch_from_configs(configs)


# Auto-register built-in strategies
def register_builtin_strategies():
    """Register built-in strategies with the registry."""
    from .rsi_strategy import RSIStrategy
    from .macd_strategy import MACDStrategy
    
    StrategyRegistry.register(StrategyType.RSI, RSIStrategy)
    StrategyRegistry.register(StrategyType.MACD, MACDStrategy)
    
    logger.info("Registered built-in strategies")


# Register on import
register_builtin_strategies()


# Convenience function
def create_strategy(strategy_type: StrategyType, **kwargs) -> Optional[BaseStrategy]:
    """
    Create a strategy instance with parameters.
    
    Args:
        strategy_type: Type of strategy
        **kwargs: Strategy parameters
        
    Returns:
        Strategy instance or None
    """
    config = StrategyConfig(
        strategy_type=strategy_type,
        enabled=True,
        parameters=kwargs
    )
    return StrategyFactory.create_from_config(config)
