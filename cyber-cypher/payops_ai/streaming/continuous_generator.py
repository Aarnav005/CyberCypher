"""Continuous payment generator with circular buffer and feedback integration."""

import logging
import time
import random
from collections import deque
from typing import List, Optional, Dict
import numpy as np

from payops_ai.models.transaction import TransactionSignal, Outcome, PaymentMethod
from payops_ai.streaming.drift_engine import StochasticDriftEngine, IssuerState

logger = logging.getLogger(__name__)


class CircularBuffer:
    """Circular buffer for maintaining recent transactions."""
    
    def __init__(self, maxsize: int = 1000):
        """Initialize circular buffer.
        
        Args:
            maxsize: Maximum number of transactions to keep
        """
        self.buffer = deque(maxlen=maxsize)
        self.maxsize = maxsize
        self.total_added = 0
    
    def add(self, transaction: TransactionSignal) -> None:
        """Add a transaction to the buffer.
        
        Args:
            transaction: Transaction to add
        """
        self.buffer.append(transaction)
        self.total_added += 1
    
    def extend(self, transactions: List[TransactionSignal]) -> None:
        """Add multiple transactions to the buffer.
        
        Args:
            transactions: List of transactions to add
        """
        self.buffer.extend(transactions)
        self.total_added += len(transactions)
    
    def get_all(self) -> List[TransactionSignal]:
        """Get all transactions in the buffer.
        
        Returns:
            List of transactions
        """
        return list(self.buffer)
    
    def get_recent(self, count: int) -> List[TransactionSignal]:
        """Get the most recent N transactions.
        
        Args:
            count: Number of transactions to retrieve
            
        Returns:
            List of recent transactions
        """
        return list(self.buffer)[-count:] if count < len(self.buffer) else list(self.buffer)
    
    def size(self) -> int:
        """Get current buffer size.
        
        Returns:
            Number of transactions in buffer
        """
        return len(self.buffer)
    
    def clear(self) -> None:
        """Clear all transactions from buffer."""
        self.buffer.clear()


class ContinuousPaymentGenerator:
    """Generates continuous payment stream with stochastic parameters and feedback."""
    
    def __init__(self, drift_engine: StochasticDriftEngine, 
                 transaction_rate: float = 20.0,
                 buffer_size: int = 1000):
        """Initialize continuous payment generator.
        
        Args:
            drift_engine: Stochastic drift engine for parameter evolution
            transaction_rate: Target transactions per second
            buffer_size: Maximum buffer size
        """
        self.drift_engine = drift_engine
        self.transaction_rate = transaction_rate
        self.buffer = CircularBuffer(maxsize=buffer_size)
        self.transaction_counter = 0
        
        # Feedback multipliers (modified by interventions)
        self.success_multipliers: Dict[str, float] = {}
        self.volume_multipliers: Dict[str, float] = {}
        self.retry_multiplier: float = 1.0
        
        logger.info(f"Initialized ContinuousPaymentGenerator: rate={transaction_rate} txns/s, buffer={buffer_size}")
    
    def set_success_multiplier(self, issuer: str, multiplier: float) -> None:
        """Set success rate multiplier for an issuer (feedback from interventions).
        
        Args:
            issuer: Issuer name
            multiplier: Success rate multiplier (0.0-1.0)
        """
        self.success_multipliers[issuer] = multiplier
        logger.info(f"Set success multiplier for {issuer}: {multiplier:.2f}")
    
    def set_volume_multiplier(self, issuer: str, multiplier: float) -> None:
        """Set volume multiplier for an issuer (feedback from interventions).
        
        Args:
            issuer: Issuer name
            multiplier: Volume multiplier (0.0-1.0)
        """
        self.volume_multipliers[issuer] = multiplier
        logger.info(f"Set volume multiplier for {issuer}: {multiplier:.2f}")
    
    def set_retry_multiplier(self, multiplier: float) -> None:
        """Set global retry multiplier (feedback from interventions).
        
        Args:
            multiplier: Retry probability multiplier (0.0-1.0)
        """
        self.retry_multiplier = multiplier
        logger.info(f"Set retry multiplier: {multiplier:.2f}")
    
    def clear_multipliers(self) -> None:
        """Clear all feedback multipliers."""
        self.success_multipliers.clear()
        self.volume_multipliers.clear()
        self.retry_multiplier = 1.0
    
    def _select_issuer_weighted(self) -> str:
        """Select an issuer using weighted random selection based on volume multipliers.
        
        Returns:
            Selected issuer name
        """
        issuers = list(self.drift_engine.issuers.keys())
        if not issuers:
            raise ValueError("No issuers configured in drift engine")
        
        # Get weights (volume multipliers)
        weights = [self.volume_multipliers.get(issuer, 1.0) for issuer in issuers]
        total_weight = sum(weights)
        
        if total_weight == 0:
            # All issuers suppressed, use uniform distribution
            return random.choice(issuers)
        
        # Normalize weights
        weights = [w / total_weight for w in weights]
        
        # Weighted random selection
        return np.random.choice(issuers, p=weights)
    
    def _generate_outcome(self, effective_success_rate: float, effective_retry_prob: float) -> Outcome:
        """Generate transaction outcome based on success rate.
        
        Args:
            effective_success_rate: Success rate after feedback adjustments
            effective_retry_prob: Retry probability after feedback adjustments
            
        Returns:
            Transaction outcome
        """
        if random.random() < effective_success_rate:
            return Outcome.SUCCESS
        else:
            # Failure - decide between soft and hard fail
            if random.random() < 0.7:  # 70% soft fails
                return Outcome.SOFT_FAIL
            else:
                return Outcome.HARD_FAIL
    
    def _generate_latency(self, base_latency: float) -> int:
        """Generate latency with some randomness around base value.
        
        Args:
            base_latency: Base latency from drift engine
            
        Returns:
            Latency in milliseconds
        """
        # Add ±20% randomness
        variation = base_latency * 0.2
        latency = base_latency + random.uniform(-variation, variation)
        return int(np.clip(latency, 50, 2000))
    
    def _generate_retries(self, effective_retry_prob: float) -> int:
        """Generate retry count based on retry probability.
        
        Args:
            effective_retry_prob: Retry probability after feedback adjustments
            
        Returns:
            Number of retries
        """
        if random.random() < effective_retry_prob:
            # Exponential distribution for retry count
            return min(int(np.random.exponential(2.0)), 10)
        return 0
    
    def generate_next_batch(self, dt: float) -> List[TransactionSignal]:
        """Generate transactions for time interval dt.
        
        Args:
            dt: Time interval in seconds
            
        Returns:
            List of generated transactions
        """
        count = int(self.transaction_rate * dt)
        if count == 0 and dt > 0:
            count = 1  # Generate at least one transaction if time has passed
        
        transactions = []
        current_time_ms = int(time.time() * 1000)
        
        for i in range(count):
            # Select issuer with volume weighting
            issuer_name = self._select_issuer_weighted()
            state = self.drift_engine.get_issuer_state(issuer_name)
            
            if not state:
                logger.warning(f"Issuer {issuer_name} not found in drift engine")
                continue
            
            # Apply feedback multipliers
            effective_success = state.success_rate * self.success_multipliers.get(issuer_name, 1.0)
            effective_success = np.clip(effective_success, 0.0, 1.0)
            
            effective_retry = state.retry_prob * self.retry_multiplier
            effective_retry = np.clip(effective_retry, 0.0, 0.5)
            
            # Generate transaction components
            outcome = self._generate_outcome(effective_success, effective_retry)
            latency = self._generate_latency(state.latency_ms)
            retry_count = self._generate_retries(effective_retry)
            
            # Create transaction
            self.transaction_counter += 1
            txn = TransactionSignal(
                transaction_id=f"txn_{current_time_ms}_{self.transaction_counter}",
                timestamp=current_time_ms + int(i * (dt * 1000 / count)),  # Spread across interval
                merchant_id=f"merchant_{random.randint(1, 20)}",
                amount=random.uniform(10.0, 1000.0),
                currency="USD",
                payment_method=PaymentMethod.CARD,
                issuer=issuer_name,
                geography=random.choice(["US", "EU", "ASIA"]),
                outcome=outcome,
                latency_ms=latency,
                retry_count=retry_count,
                error_code=None if outcome == Outcome.SUCCESS else f"ERR_{random.randint(1000, 9999)}"
            )
            transactions.append(txn)
        
        # Add to buffer
        self.buffer.extend(transactions)
        
        if transactions:
            logger.debug(f"Generated {len(transactions)} transactions in {dt:.2f}s")
        
        return transactions
    
    def get_buffer_transactions(self) -> List[TransactionSignal]:
        """Get all transactions from buffer.
        
        Returns:
            List of transactions
        """
        return self.buffer.get_all()
    
    def get_recent_transactions(self, count: int) -> List[TransactionSignal]:
        """Get recent N transactions from buffer.
        
        Args:
            count: Number of transactions to retrieve
            
        Returns:
            List of recent transactions
        """
        return self.buffer.get_recent(count)
    
    def get_buffer_size(self) -> int:
        """Get current buffer size.
        
        Returns:
            Number of transactions in buffer
        """
        return self.buffer.size()
