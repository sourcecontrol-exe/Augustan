"""
Unit tests for RiskManager class

Tests risk management calculations, validation, and error handling.
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from risk_manager import RiskManager
from exceptions import RiskManagementError, DataFetchError, ValidationError


class TestRiskManager(unittest.TestCase):
    """Test cases for RiskManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration for testing
        self.mock_config = {
            'risk_management': {
                'risk_per_trade': 0.01,
                'risk_reward_ratio': 2.0,
                'stop_loss_multiplier': 2.0
            },
            'trading': {
                'total_capital': 1000
            }
        }
        
        # Create sample OHLCV data with enough rows for ATR calculation
        dates = pd.date_range('2023-01-01', periods=20, freq='D')
        self.sample_data = pd.DataFrame({
            'open': np.random.uniform(100, 110, 20),
            'high': np.random.uniform(110, 120, 20),
            'low': np.random.uniform(90, 100, 20),
            'close': np.random.uniform(100, 110, 20),
            'volume': np.random.uniform(1000, 2000, 20)
        }, index=dates)
        
        # Ensure the data has proper relationships (high >= open,close and low <= open,close)
        for i in range(len(self.sample_data)):
            high = max(self.sample_data.iloc[i]['open'], self.sample_data.iloc[i]['close']) + np.random.uniform(0, 5)
            low = min(self.sample_data.iloc[i]['open'], self.sample_data.iloc[i]['close']) - np.random.uniform(0, 5)
            self.sample_data.iloc[i, self.sample_data.columns.get_loc('high')] = high
            self.sample_data.iloc[i, self.sample_data.columns.get_loc('low')] = low
    
    @patch('risk_manager.config')
    def test_initialization_success(self, mock_config):
        """Test successful RiskManager initialization"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        
        self.assertEqual(risk_mgr.risk_per_trade, 0.01)
        self.assertEqual(risk_mgr.risk_reward_ratio, 2.0)
        self.assertEqual(risk_mgr.stop_loss_multiplier, 2.0)
        self.assertEqual(risk_mgr.total_capital, 1000)
    
    @patch('risk_manager.config')
    def test_initialization_failure(self, mock_config):
        """Test RiskManager initialization failure"""
        mock_config.get_risk_config.side_effect = Exception("Config error")
        
        with self.assertRaises(RiskManagementError):
            RiskManager()
    
    @patch('risk_manager.config')
    def test_validation_risk_per_trade_too_high(self, mock_config):
        """Test validation with risk per trade too high"""
        invalid_config = self.mock_config.copy()
        invalid_config['risk_management']['risk_per_trade'] = 0.15
        
        mock_config.get_risk_config.return_value = invalid_config['risk_management']
        mock_config.get_trading_config.return_value = invalid_config['trading']
        
        with self.assertRaises(RiskManagementError) as context:
            RiskManager()
        
        self.assertIn("Risk per trade must be between 0 and 0.1", str(context.exception))
    
    @patch('risk_manager.config')
    def test_validation_risk_reward_ratio_invalid(self, mock_config):
        """Test validation with invalid risk-reward ratio"""
        invalid_config = self.mock_config.copy()
        invalid_config['risk_management']['risk_reward_ratio'] = 0.3
        
        mock_config.get_risk_config.return_value = invalid_config['risk_management']
        mock_config.get_trading_config.return_value = invalid_config['trading']
        
        with self.assertRaises(RiskManagementError) as context:
            RiskManager()
        
        self.assertIn("Risk-reward ratio must be between 0.5 and 10.0", str(context.exception))
    
    @patch('risk_manager.config')
    def test_validation_stop_loss_multiplier_invalid(self, mock_config):
        """Test validation with invalid stop-loss multiplier"""
        invalid_config = self.mock_config.copy()
        invalid_config['risk_management']['stop_loss_multiplier'] = 6.0
        
        mock_config.get_risk_config.return_value = invalid_config['risk_management']
        mock_config.get_trading_config.return_value = invalid_config['trading']
        
        with self.assertRaises(RiskManagementError) as context:
            RiskManager()
        
        self.assertIn("Stop-loss multiplier must be between 0.5 and 5.0", str(context.exception))
    
    @patch('risk_manager.config')
    def test_validation_total_capital_invalid(self, mock_config):
        """Test validation with invalid total capital"""
        invalid_config = self.mock_config.copy()
        invalid_config['trading']['total_capital'] = -100
        
        mock_config.get_risk_config.return_value = invalid_config['risk_management']
        mock_config.get_trading_config.return_value = invalid_config['trading']
        
        with self.assertRaises(RiskManagementError) as context:
            RiskManager()
        
        self.assertIn("Total capital must be positive", str(context.exception))
    
    @patch('risk_manager.config')
    def test_calculate_trade_details_buy_signal(self, mock_config):
        """Test trade details calculation for BUY signal"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        result = risk_mgr.calculate_trade_details(self.sample_data, 'BUY')
        
        self.assertIsNotNone(result)
        self.assertIn('position_size', result)
        self.assertIn('stop_loss', result)
        self.assertIn('take_profit', result)
        self.assertIn('entry_price', result)
        
        # Verify calculations
        current_price = self.sample_data['close'].iloc[-1]
        self.assertGreater(result['position_size'], 0)
        self.assertLess(result['stop_loss'], current_price)  # Stop loss below entry for BUY
        self.assertGreater(result['take_profit'], current_price)  # Take profit above entry for BUY
        self.assertEqual(result['entry_price'], current_price)
    
    @patch('risk_manager.config')
    def test_calculate_trade_details_sell_signal(self, mock_config):
        """Test trade details calculation for SELL signal"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        result = risk_mgr.calculate_trade_details(self.sample_data, 'SELL')
        
        self.assertIsNotNone(result)
        
        # Verify calculations for SELL
        current_price = self.sample_data['close'].iloc[-1]
        self.assertGreater(result['position_size'], 0)
        self.assertGreater(result['stop_loss'], current_price)  # Stop loss above entry for SELL
        self.assertLess(result['take_profit'], current_price)  # Take profit below entry for SELL
    
    @patch('risk_manager.config')
    def test_calculate_trade_details_empty_dataframe(self, mock_config):
        """Test trade details calculation with empty DataFrame"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        empty_df = pd.DataFrame()
        
        with self.assertRaises(DataFetchError) as context:
            risk_mgr.calculate_trade_details(empty_df, 'BUY')
        
        self.assertIn("OHLCV DataFrame is empty", str(context.exception))
    
    @patch('risk_manager.config')
    def test_calculate_trade_details_invalid_signal(self, mock_config):
        """Test trade details calculation with invalid signal"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        
        with self.assertRaises(ValidationError) as context:
            risk_mgr.calculate_trade_details(self.sample_data, 'INVALID')
        
        self.assertIn("Invalid signal: INVALID", str(context.exception))
    
    @patch('risk_manager.config')
    def test_calculate_trade_details_invalid_atr(self, mock_config):
        """Test trade details calculation with invalid ATR"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        
        # Create data with invalid ATR by making all values the same
        invalid_data = pd.DataFrame({
            'open': [100] * 20,
            'high': [100] * 20,
            'low': [100] * 20,
            'close': [100] * 20,
            'volume': [1000] * 20
        })
        
        with self.assertRaises(DataFetchError) as context:
            risk_mgr.calculate_trade_details(invalid_data, 'BUY')
        
        self.assertIn("Invalid ATR value", str(context.exception))
    
    @patch('risk_manager.config')
    def test_calculate_portfolio_risk(self, mock_config):
        """Test portfolio risk calculation"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        
        # Mock positions
        positions = [
            {'size': 10, 'current_price': 100},  # Value: 1000
            {'size': 5, 'current_price': 200}    # Value: 1000
        ]
        
        result = risk_mgr.calculate_portfolio_risk(positions)
        
        self.assertIn('total_exposure', result)
        self.assertIn('total_risk', result)
        self.assertIn('portfolio_risk', result)
        self.assertIn('exposure_ratio', result)
        self.assertIn('available_capital', result)
        
        # Verify calculations
        self.assertEqual(result['total_exposure'], 2000)  # 1000 + 1000
        self.assertEqual(result['total_risk'], 20)        # 2000 * 0.01
        self.assertEqual(result['portfolio_risk'], 0.02)  # 20 / 1000
        self.assertEqual(result['exposure_ratio'], 2.0)   # 2000 / 1000
        self.assertEqual(result['available_capital'], -1000)  # 1000 - 2000
    
    @patch('risk_manager.config')
    def test_adjust_position_size(self, mock_config):
        """Test position size adjustment based on volatility"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        
        # Test with low volatility
        adjusted_size = risk_mgr.adjust_position_size(100, 0.1)
        self.assertGreaterEqual(adjusted_size, 95)  # Should be close to original
        
        # Test with high volatility
        adjusted_size = risk_mgr.adjust_position_size(100, 0.9)
        self.assertLess(adjusted_size, 60)  # Should be significantly reduced
    
    @patch('risk_manager.config')
    def test_adjust_position_size_invalid_volatility(self, mock_config):
        """Test position size adjustment with invalid volatility"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        
        with self.assertRaises(RiskManagementError) as context:
            risk_mgr.adjust_position_size(100, 1.5)
        
        self.assertIn("Market volatility must be between 0 and 1", str(context.exception))
    
    @patch('risk_manager.config')
    def test_get_risk_summary(self, mock_config):
        """Test risk summary retrieval"""
        mock_config.get_risk_config.return_value = self.mock_config['risk_management']
        mock_config.get_trading_config.return_value = self.mock_config['trading']
        
        risk_mgr = RiskManager()
        summary = risk_mgr.get_risk_summary()
        
        expected_summary = {
            'risk_per_trade': 0.01,
            'risk_reward_ratio': 2.0,
            'stop_loss_multiplier': 2.0,
            'total_capital': 1000,
            'max_risk_per_trade': 10.0  # 1000 * 0.01
        }
        
        self.assertEqual(summary, expected_summary)


if __name__ == '__main__':
    unittest.main()
