"""Realistic payment data generator for streaming simulation."""

import random
import time
from typing import Dict, Any, List
from datetime import datetime


class PaymentDataGenerator:
    """Generates realistic payment transaction data that mirrors production telemetry."""
    
    # Realistic issuer distribution (based on Indian payment ecosystem)
    ISSUERS = {
        "HDFC": 0.25,      # 25% market share
        "ICICI": 0.20,     # 20%
        "SBI": 0.18,       # 18%
        "Axis": 0.12,      # 12%
        "Kotak": 0.10,     # 10%
        "PNB": 0.08,       # 8%
        "BOB": 0.07,       # 7%
    }
    
    # Payment methods distribution
    PAYMENT_METHODS = {
        "card": 0.45,      # 45% cards
        "upi": 0.35,       # 35% UPI
        "wallet": 0.12,    # 12% wallets
        "netbanking": 0.08 # 8% net banking
    }
    
    # Error codes with realistic probabilities
    ERROR_CODES = {
        "ISSUER_DOWN": 0.30,
        "TIMEOUT": 0.25,
        "INSUFFICIENT_FUNDS": 0.20,
        "503_SERVICE_UNAVAILABLE": 0.15,
        "NETWORK_ERROR": 0.10,
    }
    
    # Merchant categories
    MERCHANT_CATEGORIES = [
        "ecommerce", "food_delivery", "travel", "utilities", 
        "entertainment", "education", "healthcare", "retail"
    ]
    
    def __init__(self, base_success_rate: float = 0.95):
        """Initialize payment generator.
        
        Args:
            base_success_rate: Base success rate for normal operations
        """
        self.base_success_rate = base_success_rate
        self.transaction_counter = 0
        
        # Scenario configurations
        self.scenarios = {
            "normal": {"success_rate": 0.95, "avg_latency": 150, "retry_rate": 0.05},
            "hdfc_degradation": {"success_rate": 0.35, "avg_latency": 3500, "retry_rate": 0.60, "affected_issuer": "HDFC"},
            "retry_storm": {"success_rate": 0.55, "avg_latency": 200, "retry_rate": 0.80},
            "method_fatigue": {"success_rate": 0.62, "avg_latency": 180, "retry_rate": 0.35, "affected_method": "wallet"},
            "black_friday": {"success_rate": 0.70, "avg_latency": 2500, "retry_rate": 0.45, "high_volume": True},
        }
        
        self.current_scenario = "normal"
    
    def set_scenario(self, scenario: str):
        """Set current scenario for data generation.
        
        Args:
            scenario: Scenario name (normal, hdfc_degradation, retry_storm, etc.)
        """
        if scenario in self.scenarios:
            self.current_scenario = scenario
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
    
    def _select_weighted(self, distribution: Dict[str, float]) -> str:
        """Select item based on weighted distribution."""
        items = list(distribution.keys())
        weights = list(distribution.values())
        return random.choices(items, weights=weights)[0]
    
    def _get_time_of_day_multiplier(self) -> float:
        """Get traffic multiplier based on time of day."""
        hour = datetime.now().hour
        
        # Peak hours: 10am-2pm, 6pm-10pm
        if 10 <= hour < 14 or 18 <= hour < 22:
            return 2.5
        # Off-peak: 2am-6am
        elif 2 <= hour < 6:
            return 0.3
        # Normal hours
        else:
            return 1.0
    
    def generate_transaction(self) -> Dict[str, Any]:
        """Generate a single realistic payment transaction.
        
        Returns:
            Transaction data dictionary
        """
        self.transaction_counter += 1
        timestamp = int(time.time() * 1000)
        
        # Get scenario config
        scenario_config = self.scenarios[self.current_scenario]
        success_rate = scenario_config["success_rate"]
        avg_latency = scenario_config["avg_latency"]
        retry_rate = scenario_config["retry_rate"]
        
        # Select payment method and issuer
        payment_method = self._select_weighted(self.PAYMENT_METHODS)
        issuer = self._select_weighted(self.ISSUERS)
        
        # Apply scenario-specific modifications
        if "affected_issuer" in scenario_config and issuer == scenario_config["affected_issuer"]:
            success_rate *= 0.5  # Further degrade affected issuer
        
        if "affected_method" in scenario_config and payment_method == scenario_config["affected_method"]:
            success_rate *= 0.6  # Further degrade affected method
        
        # Determine outcome
        is_success = random.random() < success_rate
        outcome = "success" if is_success else random.choice(["soft_fail", "hard_fail"])
        
        # Generate latency (with realistic variance)
        if is_success:
            latency = int(random.gauss(avg_latency * 0.7, avg_latency * 0.2))
        else:
            latency = int(random.gauss(avg_latency * 1.5, avg_latency * 0.3))
        latency = max(50, latency)  # Minimum 50ms
        
        # Generate retry count
        if outcome == "soft_fail" and random.random() < retry_rate:
            retry_count = random.randint(1, 5)
        else:
            retry_count = 0
        
        # Select error code for failures
        error_code = None
        if not is_success:
            error_code = self._select_weighted(self.ERROR_CODES)
        
        # Generate transaction amount (realistic distribution)
        amount = round(random.lognormvariate(7.0, 1.5), 2)  # Mean ~1100, realistic distribution
        
        # Select merchant
        merchant_category = random.choice(self.MERCHANT_CATEGORIES)
        merchant_id = f"merchant_{merchant_category}_{random.randint(1, 100)}"
        
        # Build transaction
        transaction = {
            "transaction_id": f"txn_{self.current_scenario}_{self.transaction_counter}_{timestamp}",
            "timestamp": timestamp,
            "outcome": outcome,
            "error_code": error_code,
            "latency_ms": latency,
            "retry_count": retry_count,
            "payment_method": payment_method,
            "issuer": issuer,
            "merchant_id": merchant_id,
            "merchant_category": merchant_category,
            "amount": amount,
            "currency": "INR",
            "scenario": self.current_scenario,
        }
        
        return transaction
    
    def generate_batch(self, count: int) -> List[Dict[str, Any]]:
        """Generate a batch of transactions.
        
        Args:
            count: Number of transactions to generate
            
        Returns:
            List of transaction dictionaries
        """
        return [self.generate_transaction() for _ in range(count)]
    
    def get_realistic_tps(self) -> int:
        """Get realistic transactions per second based on time of day.
        
        Returns:
            Transactions per second
        """
        base_tps = 100  # Base 100 TPS
        
        if self.current_scenario == "black_friday":
            base_tps = 500  # 5x during Black Friday
        
        multiplier = self._get_time_of_day_multiplier()
        return int(base_tps * multiplier)
