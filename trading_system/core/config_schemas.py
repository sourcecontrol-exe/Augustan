"""
Configuration Schemas using Pydantic for strong typing and validation.

This module provides strongly-typed configuration schemas with validation,
documentation, and type safety using Pydantic.
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from pathlib import Path


class ExchangeCredentials(BaseModel):
    """Exchange API credentials."""
    api_key: Optional[str] = Field(None, description="Exchange API key")
    secret: Optional[str] = Field(None, description="Exchange secret key")
    testnet: bool = Field(True, description="Use testnet (default: True)")
    enabled: bool = Field(True, description="Enable this exchange")


class BinanceSpotConfig(ExchangeCredentials):
    """Binance Spot Exchange configuration."""
    exchange_type: str = "spot"


class BinanceFuturesConfig(ExchangeCredentials):
    """Binance Futures Exchange configuration."""
    exchange_type: str = "futures"


class ExchangeConfig(BaseModel):
    """Complete exchange configuration."""
    name: str = Field(..., description="Exchange name")
    spot: Optional[BinanceSpotConfig] = None
    futures: Optional[BinanceFuturesConfig] = None
    enabled: bool = Field(True, description="Enable this exchange")


class DataFetchingConfig(BaseModel):
    """Configuration for data fetching and retry logic."""
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, gt=0, description="Initial retry delay in seconds")
    backoff_multiplier: float = Field(2.0, gt=1.0, description="Exponential backoff multiplier")
    timeout_seconds: int = Field(30, gt=0, description="Request timeout in seconds")
    rate_limit_buffer: float = Field(1.2, gt=1.0, description="Rate limit safety buffer")


class SignalGenerationConfig(BaseModel):
    """Configuration for trading signal generation."""
    rsi_period: int = Field(14, ge=5, le=50, description="RSI calculation period")
    rsi_oversold: int = Field(30, ge=0, le=50, description="RSI oversold threshold")
    rsi_overbought: int = Field(70, ge=50, le=100, description="RSI overbought threshold")
    macd_fast: int = Field(12, ge=5, le=50, description="MACD fast EMA period")
    macd_slow: int = Field(26, ge=10, le=100, description="MACD slow EMA period")
    macd_signal: int = Field(9, ge=5, le=50, description="MACD signal period")
    min_signal_strength: float = Field(0.6, ge=0.0, le=1.0, description="Minimum signal strength")
    signal_cooldown_minutes: int = Field(15, ge=0, description="Cooldown between signals (minutes)")


class VolumeSettings(BaseModel):
    """Volume analysis settings."""
    min_volume_usd_24h: int = Field(1_000_000, gt=0, description="Minimum 24h volume in USD")
    min_volume_rank: int = Field(200, ge=1, description="Minimum volume rank")
    max_markets_per_exchange: int = Field(100, gt=0, description="Maximum markets to analyze per exchange")


class JobSettings(BaseModel):
    """Job execution settings."""
    schedule_time: str = Field("09:00", description="Daily job schedule time (HH:MM)")
    retention_days: int = Field(30, ge=1, description="Data retention period in days")
    output_directory: str = Field("volume_data", description="Output directory for job results")

    @validator('schedule_time')
    def validate_schedule_time(cls, v):
        """Validate schedule time format."""
        try:
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError("Must be in HH:MM format")
            hour, minute = map(int, parts)
            if not (0 <= hour <= 23):
                raise ValueError("Hour must be 0-23")
            if not (0 <= minute <= 59):
                raise ValueError("Minute must be 0-59")
            return v
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid schedule time format: {v}. Must be HH:MM. {e}")


class RiskManagementConfig(BaseModel):
    """Risk management configuration."""
    default_budget: float = Field(50.0, gt=0, description="Default trading budget")
    max_risk_per_trade: float = Field(0.002, gt=0, le=0.1, description="Maximum risk per trade (fraction)")
    min_safety_ratio: float = Field(1.5, gt=1.0, description="Minimum safety ratio for liquidation protection")
    default_leverage: int = Field(5, ge=1, le=125, description="Default leverage multiplier")
    max_position_percent: float = Field(0.1, gt=0, le=1.0, description="Maximum position size as fraction of budget")
    stop_loss_percent: float = Field(2.0, gt=0, le=10.0, description="Stop loss percentage")
    take_profit_percent: float = Field(4.0, gt=0, le=20.0, description="Take profit percentage")
    max_positions: int = Field(5, ge=1, description="Maximum concurrent positions")
    emergency_stop_loss: float = Field(10.0, gt=0, le=50.0, description="Emergency stop loss percentage")

    @validator('take_profit_percent')
    def validate_take_profit_vs_stop_loss(cls, v, values):
        """Ensure take profit is greater than stop loss."""
        if 'stop_loss_percent' in values and v <= values['stop_loss_percent']:
            raise ValueError("Take profit must be greater than stop loss")
        return v


class ExchangeConfig(BaseModel):
    """Exchange-specific configuration."""
    binance: Optional[Union[BinanceSpotConfig, BinanceFuturesConfig]] = None
    enabled: bool = Field(True, description="Enable exchange")
    testnet: bool = Field(True, description="Use testnet")
    api_key: Optional[str] = Field(None, description="API key (deprecated, use spot/futures)")
    secret: Optional[str] = Field(None, description="Secret (deprecated, use spot/futures)")


class ApplicationConfig(BaseModel):
    """Complete application configuration with validation."""
    
    # Exchange configurations
    exchanges: Dict[str, ExchangeConfig] = Field(default_factory=dict)
    
    # Core configurations
    risk_management: RiskManagementConfig = Field(default_factory=RiskManagementConfig)
    data_fetching: DataFetchingConfig = Field(default_factory=DataFetchingConfig)
    signal_generation: SignalGenerationConfig = Field(default_factory=SignalGenerationConfig)
    volume_settings: VolumeSettings = Field(default_factory=VolumeSettings)
    job_settings: JobSettings = Field(default_factory=JobSettings)
    
    # Trading mode
    trading_mode: str = Field("paper", pattern="^(paper|live)$", description="Trading mode")
    
    # Realtime settings
    realtime: Optional[Dict[str, Any]] = None
    
    @validator('trading_mode')
    def validate_trading_mode(cls, v):
        """Validate trading mode."""
        valid_modes = ['paper', 'live']
        if v not in valid_modes:
            raise ValueError(f"Trading mode must be one of: {valid_modes}")
        return v

    class Config:
        """Pydantic configuration."""
        # Allow extra fields for backward compatibility
        extra = "allow"
        # Validate assignment
        validate_assignment = True


class ConfigPaths(BaseModel):
    """Configuration file paths."""
    exchanges_config: Path = Path("config/exchanges_config.json")
    paper_trading_config: Path = Path("config/paper_trading_config.json")
    live_trading_config: Path = Path("config/live_trading_config.json")
    env_file: Path = Path(".env")

