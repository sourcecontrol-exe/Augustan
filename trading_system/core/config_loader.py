"""
Configuration Loader - Handles reading and parsing configuration files.

This module is responsible for:
- Reading JSON configuration files
- Overriding with environment variables
- Parsing into strongly-typed Pydantic models
- Validating configuration data
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Type, TypeVar
from loguru import logger
from pydantic import BaseModel, ValidationError

from .config_schemas import (
    ApplicationConfig,
    RiskManagementConfig,
    DataFetchingConfig,
    SignalGenerationConfig,
    VolumeSettings,
    JobSettings,
    ConfigPaths,
)

T = TypeVar('T', bound=BaseModel)


class ConfigLoader:
    """
    Handles loading and parsing configuration files.
    
    Responsibilities:
    - Load JSON configuration files
    - Apply environment variable overrides
    - Parse into strongly-typed Pydantic models
    - Provide validation and error handling
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing config files. Defaults to project/config/
        """
        if config_dir is None:
            # Default to project root / config
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            config_dir = project_root / "config"
        
        self.config_dir = Path(config_dir)
        self.env_file = Path(".env")
        
        logger.info(f"ConfigLoader initialized with directory: {self.config_dir}")
    
    def load_application_config(
        self, 
        config_name: str = "exchanges_config.json",
        overrides: Optional[Dict[str, Any]] = None
    ) -> ApplicationConfig:
        """
        Load complete application configuration.
        
        Args:
            config_name: Name of the config file to load
            overrides: Optional dictionary of overrides to apply
            
        Returns:
            ApplicationConfig instance with validated data
        """
        # Load raw JSON
        raw_config = self._load_json_config(config_name)
        
        # Apply environment variable overrides
        raw_config = self._apply_env_overrides(raw_config)
        
        # Apply manual overrides
        if overrides:
            raw_config.update(self._deep_merge(raw_config, overrides))
        
        try:
            # Parse into strongly-typed model
            config = ApplicationConfig(**raw_config)
            logger.info(f"Successfully loaded configuration from {config_name}")
            return config
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            # Return default config with valid values where possible
            return self._create_default_config(raw_config)
    
    def load_config_section(
        self, 
        config_name: str,
        section: str,
        model_class: Type[T]
    ) -> T:
        """
        Load a specific configuration section as a typed model.
        
        Args:
            config_name: Name of the config file
            section: Section key to extract
            model_class: Pydantic model class for the section
            
        Returns:
            Instance of the specified model class
        """
        raw_config = self._load_json_config(config_name)
        section_data = raw_config.get(section, {})
        
        try:
            return model_class(**section_data)
        except ValidationError as e:
            logger.warning(f"Failed to validate {section}: {e}. Using defaults.")
            return model_class()  # Return with defaults
    
    def _load_json_config(self, config_name: str) -> Dict[str, Any]:
        """Load and parse JSON configuration file."""
        config_path = self.config_dir / config_name
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return {}
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return {}
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Load .env file if it exists
        if self.env_file.exists():
            try:
                from dotenv import dotenv_values
                env_vars = dotenv_values(self.env_file)
                
                # Override sensitive data with environment variables
                if 'BINANCE_SPOT_API_KEY' in env_vars:
                    if 'binance' not in config:
                        config['binance'] = {}
                    config['binance']['api_key'] = env_vars['BINANCE_SPOT_API_KEY']
                
                if 'BINANCE_SPOT_SECRET_KEY' in env_vars:
                    if 'binance' not in config:
                        config['binance'] = {}
                    config['binance']['secret'] = env_vars['BINANCE_SPOT_SECRET_KEY']
                
                if 'BINANCE_TESTNET' in env_vars:
                    if 'binance' not in config:
                        config['binance'] = {}
                    config['binance']['testnet'] = env_vars['BINANCE_TESTNET'].lower() == 'true'
                
                logger.debug("Applied environment variable overrides")
            except Exception as e:
                logger.warning(f"Error loading .env file: {e}")
        
        # Apply OS environment variables
        if os.getenv('BINANCE_SPOT_API_KEY'):
            if 'binance' not in config:
                config['binance'] = {}
            config['binance']['api_key'] = os.getenv('BINANCE_SPOT_API_KEY')
        
        if os.getenv('BINANCE_SPOT_SECRET_KEY'):
            if 'binance' not in config:
                config['binance'] = {}
            config['binance']['secret'] = os.getenv('BINANCE_SPOT_SECRET_KEY')
        
        return config
    
    def _deep_merge(self, base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _create_default_config(self, raw_config: Dict[str, Any]) -> ApplicationConfig:
        """
        Create configuration with defaults, trying to preserve valid values.
        
        Args:
            raw_config: Raw config dictionary that failed validation
            
        Returns:
            ApplicationConfig with defaults and valid values from raw_config
        """
        # Try to extract what we can safely
        defaults = {
            'risk_management': raw_config.get('risk_management', {}),
            'data_fetching': raw_config.get('data_fetching', {}),
            'signal_generation': raw_config.get('signal_generation', {}),
            'volume_settings': raw_config.get('volume_settings', {}),
            'job_settings': raw_config.get('job_settings', {}),
            'trading_mode': raw_config.get('trading_mode', 'paper'),
        }
        
        # Create with defaults, ignoring invalid fields
        return ApplicationConfig(**defaults)
    
    def save_config(self, config: BaseModel, config_name: str):
        """
        Save configuration to JSON file.
        
        Args:
            config: Pydantic model instance to save
            config_name: Name of the output file
        """
        config_path = self.config_dir / config_name
        
        # Convert Pydantic model to dict and clean sensitive data
        config_dict = config.dict(exclude_none=True)
        safe_config = self._remove_sensitive_data(config_dict)
        
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(safe_config, f, indent=2, sort_keys=True)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def _remove_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data before saving."""
        sensitive_keys = ['api_key', 'secret_key', 'secret', 'password']
        
        def clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(d, dict):
                return d
            cleaned = {}
            for key, value in d.items():
                if isinstance(value, dict):
                    cleaned[key] = clean_dict(value)
                elif key.lower() in sensitive_keys:
                    cleaned[key] = "***REDACTED***"
                else:
                    cleaned[key] = value
            return cleaned
        
        return clean_dict(config)

