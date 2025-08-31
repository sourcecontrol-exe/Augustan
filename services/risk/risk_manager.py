# ==============================================================================
# File: risk_manager.py
# Description: Manages portfolio risk, position sizing, and stop-loss.
# ==============================================================================
import pandas as pd
import logging
from typing import Dict, Any, Optional
from ...core.exceptions import RiskManagementError, DataFetchError, ValidationError

# Configure logging
logger = logging.getLogger(__name__)

# Try to import pandas_ta, fallback to manual calculation if not available
try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
    logger.info("pandas_ta imported successfully")
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logger.warning("pandas_ta not available, using manual ATR calculation")

class RiskManager:
    """
    Risk management system for calculating position sizes, stop-losses, and take-profits.
    
    This class implements risk management strategies including:
    - Position sizing based on risk per trade
    - ATR-based stop-loss calculation
    - Risk-reward ratio management
    - Portfolio risk monitoring
    """
    
    def __init__(self):
        """Initialize risk manager with configuration"""
        try:
            risk_settings = config.get_risk_config()
            trading_settings = config.get_trading_config()
            
            # Load risk parameters from configuration
            self.risk_per_trade = risk_settings.get('risk_per_trade', 0.01)
            self.risk_reward_ratio = risk_settings.get('risk_reward_ratio', 2.0)
            self.stop_loss_multiplier = risk_settings.get('stop_loss_multiplier', 2.0)
            self.total_capital = trading_settings.get('total_capital', 1000)
            
            # Validate configuration
            self._validate_config()
            
            logger.info(f"RiskManager initialized - Risk per trade: {self.risk_per_trade}, "
                       f"Risk-reward ratio: {self.risk_reward_ratio}, "
                       f"Stop-loss multiplier: {self.stop_loss_multiplier}")
            
        except Exception as e:
            logger.error(f"Failed to initialize RiskManager: {e}")
            raise RiskManagementError(f"RiskManager initialization failed: {e}")
    
    def _validate_config(self):
        """Validate risk management configuration"""
        if not (0 < self.risk_per_trade <= 0.1):
            raise ValidationError(
                f"Risk per trade must be between 0 and 0.1, got {self.risk_per_trade}",
                field="risk_per_trade",
                value=self.risk_per_trade
            )
        
        if not (0.5 <= self.risk_reward_ratio <= 10.0):
            raise ValidationError(
                f"Risk-reward ratio must be between 0.5 and 10.0, got {self.risk_reward_ratio}",
                field="risk_reward_ratio",
                value=self.risk_reward_ratio
            )
        
        if not (0.5 <= self.stop_loss_multiplier <= 5.0):
            raise ValidationError(
                f"Stop-loss multiplier must be between 0.5 and 5.0, got {self.stop_loss_multiplier}",
                field="stop_loss_multiplier",
                value=self.stop_loss_multiplier
            )
        
        if self.total_capital <= 0:
            raise ValidationError(
                f"Total capital must be positive, got {self.total_capital}",
                field="total_capital",
                value=self.total_capital
            )
    
    def _calculate_atr_manual(self, df: pd.DataFrame, length: int = 14) -> pd.Series:
        """
        Calculate ATR manually if pandas_ta is not available.
        
        Args:
            df: DataFrame with OHLC data
            length: Period for ATR calculation
            
        Returns:
            Series containing ATR values
        """
        try:
            # Calculate True Range
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            
            # True Range is the maximum of the three
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            
            # Calculate ATR as simple moving average of True Range
            atr = true_range.rolling(window=length).mean()
            
            return atr
            
        except Exception as e:
            logger.error(f"Failed to calculate ATR manually: {e}")
            raise DataFetchError("Failed to calculate ATR indicator")
    
    def _calculate_atr(self, df: pd.DataFrame, length: int = 14) -> pd.Series:
        """
        Calculate ATR using available method.
        
        Args:
            df: DataFrame with OHLC data
            length: Period for ATR calculation
            
        Returns:
            Series containing ATR values
        """
        if PANDAS_TA_AVAILABLE:
            try:
                df.ta.atr(length=length, append=True)
                atr_column = f'ATR_{length}'
                if atr_column in df.columns:
                    return df[atr_column]
                else:
                    logger.warning("ATR column not found after pandas_ta calculation, using manual method")
                    return self._calculate_atr_manual(df, length)
            except Exception as e:
                logger.warning(f"pandas_ta ATR calculation failed: {e}, using manual method")
                return self._calculate_atr_manual(df, length)
        else:
            return self._calculate_atr_manual(df, length)
    
    def calculate_trade_details(self, df: pd.DataFrame, signal: str) -> Optional[Dict[str, Any]]:
        """
        Calculate position size and stop-loss for a potential trade.
        
        Args:
            df: DataFrame containing OHLCV data
            signal: Trading signal ('BUY' or 'SELL')
            
        Returns:
            Dictionary containing trade details or None if calculation fails
            
        Raises:
            DataFetchError: If OHLCV data is invalid
            RiskManagementError: If risk calculations fail
        """
        try:
            # Validate input data
            if df.empty:
                raise DataFetchError("OHLCV DataFrame is empty")
            
            if signal not in ['BUY', 'SELL']:
                raise ValidationError(
                    f"Invalid signal: {signal}. Must be 'BUY' or 'SELL'",
                    field="signal",
                    value=signal
                )
            
            # Get current price from the latest data
            current_price = df['close'].iloc[-1]
            if pd.isna(current_price) or current_price <= 0:
                raise DataFetchError(f"Invalid current price: {current_price}")
            
            # Calculate ATR
            atr_series = self._calculate_atr(df, length=14)
            atr = atr_series.iloc[-1]
            
            # Validate ATR
            if pd.isna(atr) or atr <= 0:
                raise DataFetchError(
                    f"Invalid ATR value: {atr}. ATR must be positive and non-null",
                    symbol=df.get('symbol', 'unknown'),
                    timeframe='unknown'
                )
            
            # Calculate stop-loss price based on signal and ATR
            if signal == 'BUY':
                stop_loss_price = current_price - (atr * self.stop_loss_multiplier)
            else:  # SELL
                stop_loss_price = current_price + (atr * self.stop_loss_multiplier)
            
            # Calculate price risk per unit
            price_risk_per_unit = abs(current_price - stop_loss_price)
            if price_risk_per_unit <= 0:
                raise RiskManagementError(
                    f"Invalid price risk per unit: {price_risk_per_unit}",
                    calculation_type="stop_loss_calculation"
                )
            
            # Calculate position size based on risk management rules
            risk_amount = self.total_capital * self.risk_per_trade
            position_size = risk_amount / price_risk_per_unit
            
            # Calculate take-profit price based on risk-reward ratio
            if signal == 'BUY':
                take_profit_price = current_price + (price_risk_per_unit * self.risk_reward_ratio)
            else:  # SELL
                take_profit_price = current_price - (price_risk_per_unit * self.risk_reward_ratio)
            
            # Prepare trade details
            trade_details = {
                'position_size': position_size,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'entry_price': current_price,
                'atr': atr,
                'price_risk_per_unit': price_risk_per_unit,
                'risk_amount': risk_amount
            }
            
            logger.info(f"Trade details calculated for {signal} signal: "
                       f"Position size: {position_size:.4f}, "
                       f"Stop-loss: {stop_loss_price:.4f}, "
                       f"Take-profit: {take_profit_price:.4f}")
            
            return trade_details
            
        except (DataFetchError, RiskManagementError, ValidationError):
            # Re-raise custom exceptions
            raise
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error in calculate_trade_details: {e}")
            raise RiskManagementError(f"Failed to calculate trade details: {e}")
    
    def calculate_portfolio_risk(self, positions: list) -> Dict[str, Any]:
        """
        Calculate current portfolio risk metrics.
        
        Args:
            positions: List of current positions
            
        Returns:
            Dictionary containing portfolio risk metrics
        """
        try:
            total_exposure = 0
            total_risk = 0
            
            for position in positions:
                # Calculate position exposure
                position_value = position.get('size', 0) * position.get('current_price', 0)
                total_exposure += position_value
                
                # Calculate position risk
                position_risk = position_value * self.risk_per_trade
                total_risk += position_risk
            
            # Calculate portfolio metrics
            portfolio_risk = (total_risk / self.total_capital) if self.total_capital > 0 else 0
            exposure_ratio = (total_exposure / self.total_capital) if self.total_capital > 0 else 0
            
            risk_metrics = {
                'total_exposure': total_exposure,
                'total_risk': total_risk,
                'portfolio_risk': portfolio_risk,
                'exposure_ratio': exposure_ratio,
                'available_capital': self.total_capital - total_exposure
            }
            
            logger.info(f"Portfolio risk calculated: {risk_metrics}")
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio risk: {e}")
            raise RiskManagementError(f"Portfolio risk calculation failed: {e}")
    
    def adjust_position_size(self, base_size: float, market_volatility: float) -> float:
        """
        Adjust position size based on market volatility.
        
        Args:
            base_size: Base position size
            market_volatility: Market volatility measure (0-1)
            
        Returns:
            Adjusted position size
        """
        try:
            if not (0 <= market_volatility <= 1):
                raise ValidationError(
                    f"Market volatility must be between 0 and 1, got {market_volatility}",
                    field="market_volatility",
                    value=market_volatility
                )
            
            # Reduce position size in high volatility
            volatility_factor = 1 - (market_volatility * 0.5)
            adjusted_size = base_size * volatility_factor
            
            logger.debug(f"Position size adjusted: {base_size:.4f} -> {adjusted_size:.4f} "
                        f"(volatility: {market_volatility:.2f})")
            
            return adjusted_size
            
        except Exception as e:
            logger.error(f"Failed to adjust position size: {e}")
            raise RiskManagementError(f"Position size adjustment failed: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get a summary of current risk management settings"""
        return {
            'risk_per_trade': self.risk_per_trade,
            'risk_reward_ratio': self.risk_reward_ratio,
            'stop_loss_multiplier': self.stop_loss_multiplier,
            'total_capital': self.total_capital,
            'max_risk_per_trade': self.total_capital * self.risk_per_trade
        }
