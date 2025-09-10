"""
Mock Account Service for Testnet
Provides realistic mock data for testing when SAPI endpoints are not available.
"""

import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MockAccountService:
    """Mock account service for testnet environments."""
    
    def __init__(self, initial_balance: float = 1000.0):
        """Initialize mock account service."""
        self.initial_balance = initial_balance
        self.balances = {
            'USDT': {
                'free': initial_balance,
                'used': 0.0,
                'total': initial_balance
            },
            'BTC': {
                'free': 0.01,
                'used': 0.0,
                'total': 0.01
            },
            'ETH': {
                'free': 0.1,
                'used': 0.0,
                'total': 0.1
            }
        }
        self.positions = []
        self.orders = []
        self.trades = []
        
        logger.info(f"Mock account service initialized with ${initial_balance:.2f} USDT")
    
    def get_balance(self) -> Dict:
        """Get mock account balance."""
        return {
            'info': {
                'makerCommission': 15,
                'takerCommission': 15,
                'buyerCommission': 0,
                'sellerCommission': 0,
                'canTrade': True,
                'canWithdraw': False,
                'canDeposit': False,
                'updateTime': int(datetime.now().timestamp() * 1000),
                'accountType': 'SPOT',
                'permissions': ['SPOT']
            },
            'free': self.balances,
            'used': {asset: {'free': 0.0, 'used': 0.0, 'total': 0.0} for asset in self.balances},
            'total': self.balances,
            # CCXT format compatibility
            'USDT': {
                'free': self.balances['USDT']['free'],
                'used': self.balances['USDT']['used'],
                'total': self.balances['USDT']['total']
            },
            'BTC': {
                'free': self.balances['BTC']['free'],
                'used': self.balances['BTC']['used'],
                'total': self.balances['BTC']['total']
            },
            'ETH': {
                'free': self.balances['ETH']['free'],
                'used': self.balances['ETH']['used'],
                'total': self.balances['ETH']['total']
            }
        }
    
    def get_positions(self) -> List[Dict]:
        """Get mock futures positions."""
        return [
            {
                'symbol': 'BTCUSDT',
                'initialMargin': '0.00000000',
                'maintMargin': '0.00000000',
                'unrealizedProfit': '0.00000000',
                'positionInitialMargin': '0.00000000',
                'openOrderInitialMargin': '0.00000000',
                'leverage': '5',
                'isolated': False,
                'entryPrice': '0.00000',
                'maxNotional': '5000000',
                'bidNotional': '0.00000000',
                'askNotional': '0.00000000',
                'positionSide': 'BOTH',
                'positionAmt': '0.000',
                'updateTime': int(datetime.now().timestamp() * 1000)
            }
        ]
    
    def get_orders(self) -> List[Dict]:
        """Get mock orders."""
        return []
    
    def get_trades(self) -> List[Dict]:
        """Get mock trades."""
        return []
    
    def update_balance(self, asset: str, amount: float, operation: str = 'add'):
        """Update mock balance."""
        if asset not in self.balances:
            self.balances[asset] = {'free': 0.0, 'used': 0.0, 'total': 0.0}
        
        if operation == 'add':
            self.balances[asset]['free'] += amount
            self.balances[asset]['total'] += amount
        elif operation == 'subtract':
            self.balances[asset]['free'] -= amount
            self.balances[asset]['total'] -= amount
        
        logger.info(f"Mock balance updated: {asset} {operation} {amount}")
    
    def simulate_trade(self, symbol: str, side: str, quantity: float, price: float):
        """Simulate a trade and update balances."""
        base_asset = symbol.replace('USDT', '')
        
        if side == 'BUY':
            # Buy base asset with USDT
            usdt_cost = quantity * price
            if self.balances['USDT']['free'] >= usdt_cost:
                self.update_balance('USDT', usdt_cost, 'subtract')
                self.update_balance(base_asset, quantity, 'add')
                logger.info(f"Mock trade: Bought {quantity} {base_asset} at ${price:.2f}")
            else:
                logger.warning(f"Insufficient USDT balance for mock trade")
        else:
            # Sell base asset for USDT
            usdt_gain = quantity * price
            if self.balances[base_asset]['free'] >= quantity:
                self.update_balance(base_asset, quantity, 'subtract')
                self.update_balance('USDT', usdt_gain, 'add')
                logger.info(f"Mock trade: Sold {quantity} {base_asset} at ${price:.2f}")
            else:
                logger.warning(f"Insufficient {base_asset} balance for mock trade")


def get_mock_account_service(balance: float = 1000.0) -> MockAccountService:
    """Get a mock account service instance."""
    return MockAccountService(balance)
