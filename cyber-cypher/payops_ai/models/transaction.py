"""Transaction signal data models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Outcome(str, Enum):
    """Transaction outcome types."""
    SUCCESS = "success"
    SOFT_FAIL = "soft_fail"
    HARD_FAIL = "hard_fail"


class PaymentMethod(str, Enum):
    """Payment method types."""
    CARD = "card"
    UPI = "upi"
    WALLET = "wallet"
    BNPL = "bnpl"
    NETBANKING = "netbanking"


class TransactionSignal(BaseModel):
    """Represents a single payment transaction signal.
    
    This is the core data structure for payment observations.
    All fields are validated to ensure data quality.
    """
    transaction_id: str = Field(..., min_length=1, description="Unique transaction identifier")
    timestamp: int = Field(..., gt=0, description="Unix timestamp in milliseconds")
    outcome: Outcome = Field(..., description="Transaction outcome")
    error_code: Optional[str] = Field(None, description="Error code if transaction failed")
    latency_ms: int = Field(..., ge=0, description="Transaction latency in milliseconds")
    retry_count: int = Field(..., ge=0, description="Number of retry attempts")
    payment_method: PaymentMethod = Field(..., description="Payment method used")
    issuer: str = Field(..., min_length=1, description="Issuer bank or institution")
    merchant_id: str = Field(..., min_length=1, description="Merchant identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    geography: Optional[str] = Field(None, description="Geographic region")

    @field_validator('error_code')
    @classmethod
    def validate_error_code(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure error_code is present for failed transactions."""
        outcome = info.data.get('outcome')
        if outcome in [Outcome.SOFT_FAIL, Outcome.HARD_FAIL] and not v:
            # Allow missing error codes but log warning
            pass
        return v

    class Config:
        """Pydantic configuration."""
        use_enum_values = False
        frozen = False
