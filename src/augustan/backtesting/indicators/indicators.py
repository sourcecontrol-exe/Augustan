# ==============================================================================
# File: indicators.py
# Description: Comprehensive technical indicators library for backtesting
# ==============================================================================

import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class IndicatorConfig:
    """Configuration for technical indicators"""
    name: str
    params: Dict[str, Any]
    description: str = ""


class TechnicalIndicators:
    """
    Comprehensive library of technical indicators for strategy development
    """
    
    def __init__(self):
        self.available_indicators = self._get_available_indicators()
    
    def _get_available_indicators(self) -> Dict[str, IndicatorConfig]:
        """Returns dictionary of all available indicators with their default configs"""
        return {
            # Momentum Indicators
            'rsi': IndicatorConfig('RSI', {'length': 14}, 'Relative Strength Index'),
            'stoch': IndicatorConfig('STOCH', {'k': 14, 'd': 3}, 'Stochastic Oscillator'),
            'williams_r': IndicatorConfig('WILLR', {'length': 14}, 'Williams %R'),
            'cci': IndicatorConfig('CCI', {'length': 20}, 'Commodity Channel Index'),
            'mfi': IndicatorConfig('MFI', {'length': 14}, 'Money Flow Index'),
            'roc': IndicatorConfig('ROC', {'length': 10}, 'Rate of Change'),
            
            # Trend Indicators
            'sma': IndicatorConfig('SMA', {'length': 20}, 'Simple Moving Average'),
            'ema': IndicatorConfig('EMA', {'length': 20}, 'Exponential Moving Average'),
            'wma': IndicatorConfig('WMA', {'length': 20}, 'Weighted Moving Average'),
            'macd': IndicatorConfig('MACD', {'fast': 12, 'slow': 26, 'signal': 9}, 'MACD'),
            'adx': IndicatorConfig('ADX', {'length': 14}, 'Average Directional Index'),
            'aroon': IndicatorConfig('AROON', {'length': 14}, 'Aroon Indicator'),
            'psar': IndicatorConfig('PSAR', {'af0': 0.02, 'af': 0.02, 'max_af': 0.2}, 'Parabolic SAR'),
            
            # Volatility Indicators
            'bb': IndicatorConfig('BBANDS', {'length': 20, 'std': 2}, 'Bollinger Bands'),
            'atr': IndicatorConfig('ATR', {'length': 14}, 'Average True Range'),
            'kc': IndicatorConfig('KC', {'length': 20, 'scalar': 2}, 'Keltner Channels'),
            'dc': IndicatorConfig('DC', {'length': 20}, 'Donchian Channels'),
            
            # Volume Indicators
            'obv': IndicatorConfig('OBV', {}, 'On Balance Volume'),
            'ad': IndicatorConfig('AD', {}, 'Accumulation/Distribution'),
            'cmf': IndicatorConfig('CMF', {'length': 20}, 'Chaikin Money Flow'),
            'vwap': IndicatorConfig('VWAP', {}, 'Volume Weighted Average Price'),
            'pvt': IndicatorConfig('PVT', {}, 'Price Volume Trend'),
            
            # Support/Resistance
            'pivot': IndicatorConfig('PIVOT', {}, 'Pivot Points'),
            'supertrend': IndicatorConfig('SUPERTREND', {'length': 7, 'multiplier': 3.0}, 'SuperTrend'),
            
            # Custom Indicators
            'ichimoku': IndicatorConfig('ICHIMOKU', {'tenkan': 9, 'kijun': 26, 'senkou': 52}, 'Ichimoku Cloud'),
        }
    
    def calculate_indicator(self, df: pd.DataFrame, indicator_name: str, 
                          custom_params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Calculate a specific indicator and add it to the dataframe
        
        Args:
            df: OHLCV dataframe
            indicator_name: Name of the indicator
            custom_params: Custom parameters to override defaults
            
        Returns:
            DataFrame with indicator columns added
        """
        if indicator_name not in self.available_indicators:
            raise ValueError(f"Indicator '{indicator_name}' not available")
        
        config = self.available_indicators[indicator_name]
        params = config.params.copy()
        if custom_params:
            params.update(custom_params)
        
        df_copy = df.copy()
        
        try:
            if indicator_name == 'rsi':
                df_copy.ta.rsi(length=params['length'], append=True)
            
            elif indicator_name == 'stoch':
                df_copy.ta.stoch(k=params['k'], d=params['d'], append=True)
            
            elif indicator_name == 'williams_r':
                df_copy.ta.willr(length=params['length'], append=True)
            
            elif indicator_name == 'cci':
                df_copy.ta.cci(length=params['length'], append=True)
            
            elif indicator_name == 'mfi':
                df_copy.ta.mfi(length=params['length'], append=True)
            
            elif indicator_name == 'roc':
                df_copy.ta.roc(length=params['length'], append=True)
            
            elif indicator_name == 'sma':
                df_copy.ta.sma(length=params['length'], append=True)
            
            elif indicator_name == 'ema':
                df_copy.ta.ema(length=params['length'], append=True)
            
            elif indicator_name == 'wma':
                df_copy.ta.wma(length=params['length'], append=True)
            
            elif indicator_name == 'macd':
                df_copy.ta.macd(fast=params['fast'], slow=params['slow'], 
                               signal=params['signal'], append=True)
            
            elif indicator_name == 'adx':
                df_copy.ta.adx(length=params['length'], append=True)
            
            elif indicator_name == 'aroon':
                df_copy.ta.aroon(length=params['length'], append=True)
            
            elif indicator_name == 'psar':
                df_copy.ta.psar(af0=params['af0'], af=params['af'], 
                               max_af=params['max_af'], append=True)
            
            elif indicator_name == 'bb':
                df_copy.ta.bbands(length=params['length'], std=params['std'], append=True)
            
            elif indicator_name == 'atr':
                df_copy.ta.atr(length=params['length'], append=True)
            
            elif indicator_name == 'kc':
                df_copy.ta.kc(length=params['length'], scalar=params['scalar'], append=True)
            
            elif indicator_name == 'dc':
                df_copy.ta.donchian(lower_length=params['length'], 
                                   upper_length=params['length'], append=True)
            
            elif indicator_name == 'obv':
                df_copy.ta.obv(append=True)
            
            elif indicator_name == 'ad':
                df_copy.ta.ad(append=True)
            
            elif indicator_name == 'cmf':
                df_copy.ta.cmf(length=params['length'], append=True)
            
            elif indicator_name == 'vwap':
                df_copy.ta.vwap(append=True)
            
            elif indicator_name == 'pvt':
                df_copy.ta.pvt(append=True)
            
            elif indicator_name == 'supertrend':
                df_copy.ta.supertrend(length=params['length'], 
                                     multiplier=params['multiplier'], append=True)
            
            elif indicator_name == 'ichimoku':
                df_copy.ta.ichimoku(tenkan=params['tenkan'], kijun=params['kijun'], 
                                   senkou=params['senkou'], append=True)
            
            return df_copy
            
        except Exception as e:
            raise ValueError(f"Error calculating {indicator_name}: {str(e)}")
    
    def calculate_multiple_indicators(self, df: pd.DataFrame, 
                                    indicators: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Calculate multiple indicators on the same dataframe
        
        Args:
            df: OHLCV dataframe
            indicators: List of dicts with 'name' and optional 'params'
            
        Returns:
            DataFrame with all indicator columns added
        """
        result_df = df.copy()
        
        for indicator in indicators:
            name = indicator['name']
            params = indicator.get('params', {})
            result_df = self.calculate_indicator(result_df, name, params)
        
        return result_df
    
    def get_indicator_columns(self, df: pd.DataFrame, indicator_name: str, 
                            custom_params: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Get the column names that would be created by an indicator
        
        Args:
            df: Sample dataframe
            indicator_name: Name of the indicator
            custom_params: Custom parameters
            
        Returns:
            List of column names
        """
        original_columns = set(df.columns)
        temp_df = self.calculate_indicator(df.head(50), indicator_name, custom_params)
        new_columns = [col for col in temp_df.columns if col not in original_columns]
        return new_columns
    
    def list_available_indicators(self) -> Dict[str, str]:
        """Return a dictionary of available indicators and their descriptions"""
        return {name: config.description for name, config in self.available_indicators.items()}


class CustomIndicators:
    """
    Custom indicator implementations for advanced strategies
    """
    
    @staticmethod
    def fractal_dimension(df: pd.DataFrame, length: int = 14) -> pd.Series:
        """Calculate Fractal Dimension indicator"""
        high = df['high'].rolling(window=length)
        low = df['low'].rolling(window=length)
        
        def calc_fd(series):
            if len(series) < 2:
                return np.nan
            n = len(series)
            return np.log(n) / np.log(2 * (np.max(series) - np.min(series)) / np.sum(np.abs(np.diff(series))))
        
        fd = high.apply(calc_fd, raw=False)
        return fd
    
    @staticmethod
    def market_facilitation_index(df: pd.DataFrame) -> pd.Series:
        """Calculate Market Facilitation Index"""
        return (df['high'] - df['low']) / df['volume']
    
    @staticmethod
    def ease_of_movement(df: pd.DataFrame, length: int = 14) -> pd.Series:
        """Calculate Ease of Movement indicator"""
        distance_moved = ((df['high'] + df['low']) / 2) - ((df['high'].shift(1) + df['low'].shift(1)) / 2)
        box_height = df['volume'] / (df['high'] - df['low'])
        emv = distance_moved / box_height
        return emv.rolling(window=length).mean()
    
    @staticmethod
    def price_channel_breakout(df: pd.DataFrame, length: int = 20) -> pd.DataFrame:
        """Calculate Price Channel Breakout signals"""
        highest = df['high'].rolling(window=length).max()
        lowest = df['low'].rolling(window=length).min()
        
        result = pd.DataFrame(index=df.index)
        result['upper_channel'] = highest
        result['lower_channel'] = lowest
        result['breakout_up'] = df['close'] > highest.shift(1)
        result['breakout_down'] = df['close'] < lowest.shift(1)
        
        return result
