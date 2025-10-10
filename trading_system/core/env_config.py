"""
Environment Variable Configuration Models
Secure configuration management using pydantic-settings and environment variables.
"""
import os
from typing import Optional, List, Dict, Any
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from loguru import logger


class ExchangeConfig(BaseSettings):
    """Exchange configuration from environment variables."""
    
    # Binance Configuration
    binance_api_key: Optional[str] = Field(None, env='BINANCE_API_KEY')
    binance_secret_key: Optional[str] = Field(None, env='BINANCE_SECRET_KEY')
    binance_testnet: bool = Field(True, env='BINANCE_TESTNET')
    
    # Binance Futures Configuration
    binance_futures_api_key: Optional[str] = Field(None, env='BINANCE_FUTURES_API_KEY')
    binance_futures_secret_key: Optional[str] = Field(None, env='BINANCE_FUTURES_SECRET_KEY')
    binance_futures_testnet: bool = Field(True, env='BINANCE_FUTURES_TESTNET')
    
    # Other Exchanges (for future expansion)
    coinbase_api_key: Optional[str] = Field(None, env='COINBASE_API_KEY')
    coinbase_secret_key: Optional[str] = Field(None, env='COINBASE_SECRET_KEY')
    
    kraken_api_key: Optional[str] = Field(None, env='KRAKEN_API_KEY')
    kraken_secret_key: Optional[str] = Field(None, env='KRAKEN_SECRET_KEY')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from environment


class TradingConfig(BaseSettings):
    """Trading configuration from environment variables."""
    
    # Trading Mode
    paper_trading: bool = Field(True, env='PAPER_TRADING')
    live_trading: bool = Field(False, env='LIVE_TRADING')
    
    # Account Settings
    initial_balance: float = Field(10000.0, env='INITIAL_BALANCE')
    max_position_size: float = Field(0.1, env='MAX_POSITION_SIZE')
    max_daily_loss: float = Field(0.05, env='MAX_DAILY_LOSS')
    
    # Risk Management
    max_risk_per_trade: float = Field(0.01, env='MAX_RISK_PER_TRADE')
    max_portfolio_risk: float = Field(0.1, env='MAX_PORTFOLIO_RISK')
    stop_loss_percentage: float = Field(0.02, env='STOP_LOSS_PERCENTAGE')
    take_profit_percentage: float = Field(0.04, env='TAKE_PROFIT_PERCENTAGE')
    
    # Leverage Settings
    default_leverage: int = Field(1, env='DEFAULT_LEVERAGE')
    max_leverage: int = Field(5, env='MAX_LEVERAGE')
    
    # Trading Symbols
    trading_symbols: List[str] = Field(['BTC/USDT', 'ETH/USDT'], env='TRADING_SYMBOLS')
    
    @validator('trading_symbols', pre=True)
    def parse_trading_symbols(cls, v):
        if isinstance(v, str):
            return [symbol.strip() for symbol in v.split(',')]
        return v
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from environment


class DataConfig(BaseSettings):
    """Data configuration from environment variables."""
    
    # Data Sources
    primary_exchange: str = Field('binance', env='PRIMARY_EXCHANGE')
    data_timeframes: List[str] = Field(['1m', '3m', '5m'], env='DATA_TIMEFRAMES')
    
    @validator('data_timeframes', pre=True)
    def parse_data_timeframes(cls, v):
        if isinstance(v, str):
            return [tf.strip() for tf in v.split(',')]
        return v
    
    # WebSocket Settings
    websocket_enabled: bool = Field(True, env='WEBSOCKET_ENABLED')
    websocket_reconnect_attempts: int = Field(10, env='WEBSOCKET_RECONNECT_ATTEMPTS')
    websocket_reconnect_delay: int = Field(5, env='WEBSOCKET_RECONNECT_DELAY')
    
    # Data Storage
    data_storage_path: str = Field('./data', env='DATA_STORAGE_PATH')
    enable_data_logging: bool = Field(True, env='ENABLE_DATA_LOGGING')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from environment


class LoggingConfig(BaseSettings):
    """Logging configuration from environment variables."""
    
    # Log Levels
    log_level: str = Field('INFO', env='LOG_LEVEL')
    trading_log_level: str = Field('INFO', env='TRADING_LOG_LEVEL')
    data_log_level: str = Field('DEBUG', env='DATA_LOG_LEVEL')
    
    # Log Files
    log_file_path: str = Field('./logs', env='LOG_FILE_PATH')
    log_file_max_size: str = Field('10MB', env='LOG_FILE_MAX_SIZE')
    log_file_retention: int = Field(7, env='LOG_FILE_RETENTION')
    
    # Log Formatting
    log_format: str = Field('{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}', env='LOG_FORMAT')
    enable_colors: bool = Field(True, env='ENABLE_LOG_COLORS')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from environment


class SecurityConfig(BaseSettings):
    """Security configuration from environment variables."""
    
    # API Security
    api_rate_limit: int = Field(1200, env='API_RATE_LIMIT')
    api_timeout: int = Field(30, env='API_TIMEOUT')
    enable_ssl_verification: bool = Field(True, env='ENABLE_SSL_VERIFICATION')
    
    # Secret Management
    secrets_rotation_days: int = Field(90, env='SECRETS_ROTATION_DAYS')
    encrypt_sensitive_data: bool = Field(True, env='ENCRYPT_SENSITIVE_DATA')
    
    # Access Control
    allowed_ips: List[str] = Field([], env='ALLOWED_IPS')
    
    @validator('allowed_ips', pre=True)
    def parse_allowed_ips(cls, v):
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(',') if ip.strip()]
        return v
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from environment


class DatabaseConfig(BaseSettings):
    """Database configuration from environment variables."""
    
    # Database Type
    database_type: str = Field('sqlite', env='DATABASE_TYPE')  # sqlite, postgresql, mysql
    
    # SQLite Configuration
    sqlite_path: str = Field('./data/trading.db', env='SQLITE_PATH')
    
    # PostgreSQL Configuration
    postgresql_host: Optional[str] = Field(None, env='POSTGRESQL_HOST')
    postgresql_port: int = Field(5432, env='POSTGRESQL_PORT')
    postgresql_database: Optional[str] = Field(None, env='POSTGRESQL_DATABASE')
    postgresql_username: Optional[str] = Field(None, env='POSTGRESQL_USERNAME')
    postgresql_password: Optional[str] = Field(None, env='POSTGRESQL_PASSWORD')
    
    # MySQL Configuration
    mysql_host: Optional[str] = Field(None, env='MYSQL_HOST')
    mysql_port: int = Field(3306, env='MYSQL_PORT')
    mysql_database: Optional[str] = Field(None, env='MYSQL_DATABASE')
    mysql_username: Optional[str] = Field(None, env='MYSQL_USERNAME')
    mysql_password: Optional[str] = Field(None, env='MYSQL_PASSWORD')
    
    # Connection Settings
    connection_pool_size: int = Field(10, env='CONNECTION_POOL_SIZE')
    connection_timeout: int = Field(30, env='CONNECTION_TIMEOUT')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from environment


class NotificationConfig(BaseSettings):
    """Notification configuration from environment variables."""
    
    # Email Notifications
    email_enabled: bool = Field(False, env='EMAIL_ENABLED')
    email_smtp_host: Optional[str] = Field(None, env='EMAIL_SMTP_HOST')
    email_smtp_port: int = Field(587, env='EMAIL_SMTP_PORT')
    email_username: Optional[str] = Field(None, env='EMAIL_USERNAME')
    email_password: Optional[str] = Field(None, env='EMAIL_PASSWORD')
    email_from: Optional[str] = Field(None, env='EMAIL_FROM')
    email_to: List[str] = Field([], env='EMAIL_TO')
    
    @validator('email_to', pre=True)
    def parse_email_to(cls, v):
        if isinstance(v, str):
            return [email.strip() for email in v.split(',') if email.strip()]
        return v
    
    # Slack Notifications
    slack_enabled: bool = Field(False, env='SLACK_ENABLED')
    slack_webhook_url: Optional[str] = Field(None, env='SLACK_WEBHOOK_URL')
    slack_channel: Optional[str] = Field(None, env='SLACK_CHANNEL')
    
    # Discord Notifications
    discord_enabled: bool = Field(False, env='DISCORD_ENABLED')
    discord_webhook_url: Optional[str] = Field(None, env='DISCORD_WEBHOOK_URL')
    
    # Telegram Notifications
    telegram_enabled: bool = Field(False, env='TELEGRAM_ENABLED')
    telegram_bot_token: Optional[str] = Field(None, env='TELEGRAM_BOT_TOKEN')
    telegram_chat_id: Optional[str] = Field(None, env='TELEGRAM_CHAT_ID')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from environment


class EnvironmentConfig(BaseSettings):
    """Main environment configuration aggregating all settings."""
    
    # Environment
    environment: str = Field('development', env='ENVIRONMENT')
    debug: bool = Field(False, env='DEBUG')
    
    # Component Configurations
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from environment
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate the complete configuration."""
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Validate exchange configuration
        if self.trading.live_trading:
            if not self.exchange.binance_api_key:
                validation_results['warnings'].append('Binance API key not set for live trading')
            
            if not self.exchange.binance_secret_key:
                validation_results['warnings'].append('Binance secret key not set for live trading')
        
        # Validate trading configuration
        if self.trading.max_risk_per_trade > 0.1:
            validation_results['errors'].append('Max risk per trade too high (>10%)')
            validation_results['valid'] = False
        
        if self.trading.max_portfolio_risk > 0.5:
            validation_results['errors'].append('Max portfolio risk too high (>50%)')
            validation_results['valid'] = False
        
        # Validate database configuration
        if self.database.database_type == 'postgresql':
            required_fields = ['postgresql_host', 'postgresql_database', 'postgresql_username', 'postgresql_password']
            missing_fields = [field for field in required_fields if not getattr(self.database, field)]
            if missing_fields:
                validation_results['errors'].append(f'Missing PostgreSQL configuration: {missing_fields}')
                validation_results['valid'] = False
        
        return validation_results
    
    def get_exchange_credentials(self, exchange_name: str) -> Dict[str, str]:
        """Get exchange credentials for a specific exchange."""
        credentials = {}
        
        if exchange_name.lower() == 'binance':
            if self.exchange.binance_api_key:
                credentials['api_key'] = self.exchange.binance_api_key
            if self.exchange.binance_secret_key:
                credentials['secret'] = self.exchange.binance_secret_key
            credentials['testnet'] = self.exchange.binance_testnet
        
        elif exchange_name.lower() == 'binance_futures':
            if self.exchange.binance_futures_api_key:
                credentials['api_key'] = self.exchange.binance_futures_api_key
            if self.exchange.binance_futures_secret_key:
                credentials['secret'] = self.exchange.binance_futures_secret_key
            credentials['testnet'] = self.exchange.binance_futures_testnet
        
        elif exchange_name.lower() == 'coinbase':
            if self.exchange.coinbase_api_key:
                credentials['api_key'] = self.exchange.coinbase_api_key
            if self.exchange.coinbase_secret_key:
                credentials['secret'] = self.exchange.coinbase_secret_key
        
        elif exchange_name.lower() == 'kraken':
            if self.exchange.kraken_api_key:
                credentials['api_key'] = self.exchange.kraken_api_key
            if self.exchange.kraken_secret_key:
                credentials['secret'] = self.exchange.kraken_secret_key
        
        return credentials
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == 'development'
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() == 'testing'


# Global configuration instance
_config_instance: Optional[EnvironmentConfig] = None


def get_environment_config() -> EnvironmentConfig:
    """Get the global environment configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = EnvironmentConfig()
        logger.info(f"Environment configuration loaded: {_config_instance.environment}")
    return _config_instance


def reload_environment_config() -> EnvironmentConfig:
    """Reload the environment configuration."""
    global _config_instance
    _config_instance = EnvironmentConfig()
    logger.info(f"Environment configuration reloaded: {_config_instance.environment}")
    return _config_instance


def validate_environment() -> bool:
    """Validate the current environment configuration."""
    config = get_environment_config()
    validation = config.validate_configuration()
    
    if validation['warnings']:
        for warning in validation['warnings']:
            logger.warning(f"Configuration warning: {warning}")
    
    if validation['errors']:
        for error in validation['errors']:
            logger.error(f"Configuration error: {error}")
        return False
    
    logger.info("Environment configuration validation passed")
    return True
