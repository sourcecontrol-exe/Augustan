"""
OrderBook - Core order book management with sorted bids and asks.

This module provides the fundamental order book data structure that maintains
sorted bid and ask orders, ensuring data integrity and efficient price discovery.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from collections import OrderedDict
import heapq
from loguru import logger


@dataclass
class OrderLevel:
    """Represents a price level in the order book."""
    price: float
    quantity: float
    timestamp: datetime
    
    def __post_init__(self):
        """Validate order level data."""
        if self.price <= 0:
            raise ValueError(f"Price must be positive, got {self.price}")
        if self.quantity < 0:
            raise ValueError(f"Quantity must be non-negative, got {self.quantity}")


class OrderBook:
    """
    Order book maintaining sorted bids and asks.
    
    Features:
    - Automatically sorted bids (highest first) and asks (lowest first)
    - Efficient add/update/delete operations
    - Data integrity validation
    - Spread calculation
    - Best bid/ask access
    - Volume-weighted average price (VWAP) calculation
    """
    
    def __init__(self, symbol: str, max_levels: int = 1000):
        """
        Initialize order book.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            max_levels: Maximum number of price levels to maintain
        """
        self.symbol = symbol
        self.max_levels = max_levels
        self.last_update = datetime.now()
        
        # Bids: OrderedDict with price as key, OrderLevel as value
        # Automatically sorted by price (highest first)
        self.bids: OrderedDict[float, OrderLevel] = OrderedDict()
        
        # Asks: OrderedDict with price as key, OrderLevel as value  
        # Automatically sorted by price (lowest first)
        self.asks: OrderedDict[float, OrderLevel] = OrderedDict()
        
        # Track order book state for integrity checks
        self.update_count = 0
        self.last_sequence = 0
        
        logger.debug(f"OrderBook initialized for {symbol}")
    
    def update(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]], 
               sequence: Optional[int] = None) -> bool:
        """
        Update the entire order book with new bid/ask data.
        
        Args:
            bids: List of (price, quantity) tuples for bids
            asks: List of (price, quantity) tuples for asks
            sequence: Optional sequence number for integrity checks
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Validate sequence number
            if sequence is not None and sequence <= self.last_sequence:
                logger.warning(f"Out-of-sequence update: {sequence} <= {self.last_sequence}")
                return False
            
            # Clear existing data
            self.bids.clear()
            self.asks.clear()
            
            # Add bids (sorted by price descending)
            for price, quantity in bids:
                if quantity > 0:  # Only add non-zero quantities
                    self._add_bid(price, quantity)
            
            # Add asks (sorted by price ascending)
            for price, quantity in asks:
                if quantity > 0:  # Only add non-zero quantities
                    self._add_ask(price, quantity)
            
            # Update metadata
            self.last_update = datetime.now()
            self.update_count += 1
            if sequence is not None:
                self.last_sequence = sequence
            
            # Validate data integrity
            if not self._validate_integrity():
                logger.error("Order book integrity validation failed")
                return False
            
            logger.debug(f"Order book updated: {len(self.bids)} bids, {len(self.asks)} asks")
            return True
            
        except Exception as e:
            logger.error(f"Error updating order book: {e}")
            return False
    
    def handle_update(self, side: str, price: float, quantity: float, 
                     sequence: Optional[int] = None) -> bool:
        """
        Handle incremental order book update.
        
        Args:
            side: 'bid' or 'ask'
            price: Order price
            quantity: Order quantity (0 to delete)
            sequence: Optional sequence number
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Validate sequence
            if sequence is not None and sequence <= self.last_sequence:
                logger.warning(f"Out-of-sequence update: {sequence} <= {self.last_sequence}")
                return False
            
            # Validate inputs
            if price <= 0:
                logger.error(f"Invalid price: {price}")
                return False
            
            if quantity < 0:
                logger.error(f"Invalid quantity: {quantity}")
                return False
            
            # Handle the update
            if side.lower() == 'bid':
                if quantity == 0:
                    self._delete_bid(price)
                else:
                    self._add_bid(price, quantity)
            elif side.lower() == 'ask':
                if quantity == 0:
                    self._delete_ask(price)
                else:
                    self._add_ask(price, quantity)
            else:
                logger.error(f"Invalid side: {side}")
                return False
            
            # Update metadata
            self.last_update = datetime.now()
            self.update_count += 1
            if sequence is not None:
                self.last_sequence = sequence
            
            # Validate integrity
            if not self._validate_integrity():
                logger.error("Order book integrity validation failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling update: {e}")
            return False
    
    def add(self, side: str, price: float, quantity: float) -> bool:
        """
        Add a new order to the book.
        
        Args:
            side: 'bid' or 'ask'
            price: Order price
            quantity: Order quantity
            
        Returns:
            True if order was added successfully
        """
        return self.handle_update(side, price, quantity)
    
    def delete(self, side: str, price: float) -> bool:
        """
        Delete an order from the book.
        
        Args:
            side: 'bid' or 'ask'
            price: Order price to delete
            
        Returns:
            True if order was deleted successfully
        """
        return self.handle_update(side, price, 0.0)
    
    def _add_bid(self, price: float, quantity: float):
        """Add a bid order, maintaining sorted order."""
        order_level = OrderLevel(price, quantity, datetime.now())
        
        # Insert in sorted order (highest price first)
        if not self.bids or price > next(iter(self.bids.keys())):
            # New highest bid
            self.bids[price] = order_level
            # Move to front
            self.bids.move_to_end(price, last=False)
        else:
            # Insert in correct position
            temp_bids = OrderedDict()
            inserted = False
            
            for existing_price, existing_level in self.bids.items():
                if not inserted and price > existing_price:
                    temp_bids[price] = order_level
                    inserted = True
                temp_bids[existing_price] = existing_level
            
            if not inserted:
                temp_bids[price] = order_level
            
            self.bids = temp_bids
        
        # Limit number of levels
        if len(self.bids) > self.max_levels:
            # Remove lowest bid
            self.bids.popitem(last=True)
    
    def _add_ask(self, price: float, quantity: float):
        """Add an ask order, maintaining sorted order."""
        order_level = OrderLevel(price, quantity, datetime.now())
        
        # Insert in sorted order (lowest price first)
        if not self.asks or price < next(iter(self.asks.keys())):
            # New lowest ask
            self.asks[price] = order_level
            # Move to front
            self.asks.move_to_end(price, last=False)
        else:
            # Insert in correct position
            temp_asks = OrderedDict()
            inserted = False
            
            for existing_price, existing_level in self.asks.items():
                if not inserted and price < existing_price:
                    temp_asks[price] = order_level
                    inserted = True
                temp_asks[existing_price] = existing_level
            
            if not inserted:
                temp_asks[price] = order_level
            
            self.asks = temp_asks
        
        # Limit number of levels
        if len(self.asks) > self.max_levels:
            # Remove highest ask
            self.asks.popitem(last=True)
    
    def _delete_bid(self, price: float):
        """Delete a bid order."""
        if price in self.bids:
            del self.bids[price]
    
    def _delete_ask(self, price: float):
        """Delete an ask order."""
        if price in self.asks:
            del self.asks[price]
    
    def _validate_integrity(self) -> bool:
        """Validate order book data integrity."""
        try:
            # Check that bids are sorted (highest first)
            bid_prices = list(self.bids.keys())
            if bid_prices != sorted(bid_prices, reverse=True):
                logger.error("Bids are not sorted correctly")
                return False
            
            # Check that asks are sorted (lowest first)
            ask_prices = list(self.asks.keys())
            if ask_prices != sorted(ask_prices):
                logger.error("Asks are not sorted correctly")
                return False
            
            # Check for cross (bid >= ask)
            if self.bids and self.asks:
                best_bid = max(self.bids.keys())
                best_ask = min(self.asks.keys())
                if best_bid >= best_ask:
                    logger.warning(f"Cross detected: bid {best_bid} >= ask {best_ask}")
                    # This might be acceptable in some cases (e.g., during fast markets)
            
            return True
            
        except Exception as e:
            logger.error(f"Integrity validation error: {e}")
            return False
    
    def get_best_bid(self) -> Optional[Tuple[float, float]]:
        """Get the best bid (highest price and quantity)."""
        if not self.bids:
            return None
        best_price = max(self.bids.keys())
        return (best_price, self.bids[best_price].quantity)
    
    def get_best_ask(self) -> Optional[Tuple[float, float]]:
        """Get the best ask (lowest price and quantity)."""
        if not self.asks:
            return None
        best_price = min(self.asks.keys())
        return (best_price, self.asks[best_price].quantity)
    
    def get_spread(self) -> Optional[float]:
        """Get the bid-ask spread."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask[0] - best_bid[0]
        return None
    
    def get_mid_price(self) -> Optional[float]:
        """Get the mid price (average of best bid and ask)."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return (best_bid[0] + best_ask[0]) / 2
        return None
    
    def get_vwap(self, side: str, depth: int = 10) -> Optional[float]:
        """
        Calculate Volume Weighted Average Price.
        
        Args:
            side: 'bid' or 'ask'
            depth: Number of levels to include
            
        Returns:
            VWAP or None if insufficient data
        """
        try:
            if side.lower() == 'bid':
                levels = list(self.bids.items())[:depth]
            elif side.lower() == 'ask':
                levels = list(self.asks.items())[:depth]
            else:
                return None
            
            if not levels:
                return None
            
            total_volume = sum(level.quantity for _, level in levels)
            if total_volume == 0:
                return None
            
            weighted_price = sum(price * level.quantity for price, level in levels)
            return weighted_price / total_volume
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return None
    
    def get_depth(self, side: str, depth: int = 10) -> List[Tuple[float, float]]:
        """
        Get order book depth.
        
        Args:
            side: 'bid' or 'ask'
            depth: Number of levels to return
            
        Returns:
            List of (price, quantity) tuples
        """
        try:
            if side.lower() == 'bid':
                levels = list(self.bids.items())[:depth]
            elif side.lower() == 'ask':
                levels = list(self.asks.items())[:depth]
            else:
                return []
            
            return [(price, level.quantity) for price, level in levels]
            
        except Exception as e:
            logger.error(f"Error getting depth: {e}")
            return []
    
    def get_total_volume(self, side: str, depth: int = 10) -> float:
        """Get total volume for a side up to specified depth."""
        levels = self.get_depth(side, depth)
        return sum(quantity for _, quantity in levels)
    
    def is_empty(self) -> bool:
        """Check if order book is empty."""
        return len(self.bids) == 0 and len(self.asks) == 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get order book statistics."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        spread = self.get_spread()
        mid_price = self.get_mid_price()
        
        return {
            'symbol': self.symbol,
            'bid_count': len(self.bids),
            'ask_count': len(self.asks),
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread': spread,
            'mid_price': mid_price,
            'bid_vwap': self.get_vwap('bid'),
            'ask_vwap': self.get_vwap('ask'),
            'total_bid_volume': self.get_total_volume('bid'),
            'total_ask_volume': self.get_total_volume('ask'),
            'last_update': self.last_update.isoformat(),
            'update_count': self.update_count,
            'last_sequence': self.last_sequence
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order book to dictionary representation."""
        return {
            'symbol': self.symbol,
            'bids': [(price, level.quantity) for price, level in self.bids.items()],
            'asks': [(price, level.quantity) for price, level in self.asks.items()],
            'last_update': self.last_update.isoformat(),
            'update_count': self.update_count,
            'last_sequence': self.last_sequence
        }
