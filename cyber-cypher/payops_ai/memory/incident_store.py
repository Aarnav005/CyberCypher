"""Incident storage with temporal and contextual indexing."""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class IncidentSignature:
    """Represents a unique incident signature for matching."""
    
    def __init__(
        self,
        error_code: str,
        issuer: str,
        payment_method: str,
        failure_rate: float,
        time_of_day: str,  # morning, afternoon, evening, night
        day_of_week: str,
        season: str,  # regular, black_friday, holiday, etc.
    ):
        self.error_code = error_code
        self.issuer = issuer
        self.payment_method = payment_method
        self.failure_rate = failure_rate
        self.time_of_day = time_of_day
        self.day_of_week = day_of_week
        self.season = season
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_code": self.error_code,
            "issuer": self.issuer,
            "payment_method": self.payment_method,
            "failure_rate": self.failure_rate,
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
            "season": self.season,
        }
    
    def similarity(self, other: "IncidentSignature") -> float:
        """Calculate similarity score with another signature."""
        score = 0.0
        weights = {
            "error_code": 0.3,
            "issuer": 0.2,
            "payment_method": 0.15,
            "failure_rate": 0.15,
            "time_of_day": 0.1,
            "day_of_week": 0.05,
            "season": 0.05,
        }
        
        # Exact matches
        if self.error_code == other.error_code:
            score += weights["error_code"]
        if self.issuer == other.issuer:
            score += weights["issuer"]
        if self.payment_method == other.payment_method:
            score += weights["payment_method"]
        if self.time_of_day == other.time_of_day:
            score += weights["time_of_day"]
        if self.day_of_week == other.day_of_week:
            score += weights["day_of_week"]
        if self.season == other.season:
            score += weights["season"]
        
        # Failure rate similarity (within 10%)
        if abs(self.failure_rate - other.failure_rate) < 0.1:
            score += weights["failure_rate"]
        
        return score


class HistoricalIncident:
    """Represents a historical incident with resolution."""
    
    def __init__(
        self,
        incident_id: str,
        signature: IncidentSignature,
        timestamp: int,
        description: str,
        intervention_taken: str,
        outcome: str,
        success: bool,
        resolution_time_minutes: int,
        lessons_learned: List[str],
        telemetry: Dict[str, Any],
    ):
        self.incident_id = incident_id
        self.signature = signature
        self.timestamp = timestamp
        self.description = description
        self.intervention_taken = intervention_taken
        self.outcome = outcome
        self.success = success
        self.resolution_time_minutes = resolution_time_minutes
        self.lessons_learned = lessons_learned
        self.telemetry = telemetry
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "incident_id": self.incident_id,
            "signature": self.signature.to_dict(),
            "timestamp": self.timestamp,
            "description": self.description,
            "intervention_taken": self.intervention_taken,
            "outcome": self.outcome,
            "success": self.success,
            "resolution_time_minutes": self.resolution_time_minutes,
            "lessons_learned": self.lessons_learned,
            "telemetry": self.telemetry,
        }


class IncidentStore:
    """Stores and retrieves historical incidents with temporal context."""
    
    def __init__(self):
        """Initialize incident store."""
        self.incidents: List[HistoricalIncident] = []
        self.incident_index: Dict[str, HistoricalIncident] = {}
        self.signature_index: Dict[str, List[HistoricalIncident]] = defaultdict(list)
        
        # Load some example historical incidents
        self._load_example_incidents()
    
    def _load_example_incidents(self):
        """Load example historical incidents for demonstration."""
        
        # Black Friday 2023 - HDFC Outage
        incident1 = HistoricalIncident(
            incident_id="INC-2023-BF-001",
            signature=IncidentSignature(
                error_code="503_SERVICE_UNAVAILABLE",
                issuer="HDFC",
                payment_method="card",
                failure_rate=0.65,
                time_of_day="morning",
                day_of_week="Friday",
                season="black_friday"
            ),
            timestamp=1700809200000,  # Black Friday 2023
            description="HDFC Bank API experiencing 503 errors during Black Friday peak traffic",
            intervention_taken="suppress_path",
            outcome="Suppressed HDFC for 15 minutes, rerouted to ICICI and SBI. Success rate recovered to 92%",
            success=True,
            resolution_time_minutes=15,
            lessons_learned=[
                "HDFC struggles with Black Friday traffic spikes",
                "Rerouting to ICICI+SBI combination works well",
                "15-minute suppression is optimal - longer causes user friction",
                "Monitor queue depth as early warning signal"
            ],
            telemetry={
                "peak_tps": 5000,
                "queue_depth_before": 2500,
                "queue_depth_after": 800,
                "latency_p95_before": 3500,
                "latency_p95_after": 450
            }
        )
        self.add_incident(incident1)
        
        # Monday Morning - Retry Storm
        incident2 = HistoricalIncident(
            incident_id="INC-2024-01-MON-001",
            signature=IncidentSignature(
                error_code="TIMEOUT",
                issuer="ICICI",
                payment_method="upi",
                failure_rate=0.45,
                time_of_day="morning",
                day_of_week="Monday",
                season="regular"
            ),
            timestamp=1704700800000,  # Monday morning
            description="UPI retry storm on Monday morning causing cascading failures",
            intervention_taken="reduce_retry_attempts",
            outcome="Reduced max retries from 5 to 2. Storm subsided in 8 minutes",
            success=True,
            resolution_time_minutes=8,
            lessons_learned=[
                "Monday mornings see 3x normal UPI traffic",
                "ICICI UPI has lower capacity on Monday 8-10am",
                "Reducing retries breaks the storm cycle",
                "Preemptively reduce retries on Monday mornings"
            ],
            telemetry={
                "avg_retry_count_before": 4.2,
                "avg_retry_count_after": 1.8,
                "success_rate_before": 0.55,
                "success_rate_after": 0.88
            }
        )
        self.add_incident(incident2)
        
        # Holiday Season - Method Fatigue
        incident3 = HistoricalIncident(
            incident_id="INC-2023-DEC-HOL-001",
            signature=IncidentSignature(
                error_code="INSUFFICIENT_FUNDS",
                issuer="SBI",
                payment_method="wallet",
                failure_rate=0.38,
                time_of_day="evening",
                day_of_week="Saturday",
                season="holiday"
            ),
            timestamp=1703347200000,  # Holiday season
            description="Wallet payment failures during holiday shopping peak",
            intervention_taken="reroute_traffic",
            outcome="Suggested alternative payment methods. Conversion improved by 15%",
            success=True,
            resolution_time_minutes=5,
            lessons_learned=[
                "Holiday season sees wallet balance exhaustion",
                "Evening shopping peaks have higher wallet failures",
                "Proactive method suggestion improves conversion",
                "Card fallback works better than UPI for high-value transactions"
            ],
            telemetry={
                "avg_transaction_amount": 8500,
                "wallet_balance_avg": 2000,
                "card_fallback_success": 0.92
            }
        )
        self.add_incident(incident3)
        
        logger.info(f"Loaded {len(self.incidents)} example historical incidents")
    
    def add_incident(self, incident: HistoricalIncident):
        """Add incident to store."""
        self.incidents.append(incident)
        self.incident_index[incident.incident_id] = incident
        
        # Index by error code for fast lookup
        key = f"{incident.signature.error_code}_{incident.signature.issuer}"
        self.signature_index[key].append(incident)
    
    def find_similar_incidents(
        self,
        current_signature: IncidentSignature,
        top_k: int = 3,
        min_similarity: float = 0.5
    ) -> List[tuple[HistoricalIncident, float]]:
        """Find similar historical incidents using signature matching.
        
        Args:
            current_signature: Current incident signature
            top_k: Number of top matches to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (incident, similarity_score) tuples
        """
        matches = []
        
        for incident in self.incidents:
            similarity = current_signature.similarity(incident.signature)
            if similarity >= min_similarity:
                matches.append((incident, similarity))
        
        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches[:top_k]
    
    def get_seasonal_context(self, timestamp: int) -> str:
        """Determine seasonal context from timestamp."""
        dt = datetime.fromtimestamp(timestamp / 1000)
        
        # Check for special seasons
        if dt.month == 11 and dt.day >= 24:  # Black Friday
            return "black_friday"
        elif dt.month == 12:  # Holiday season
            return "holiday"
        elif dt.month == 1 and dt.day <= 7:  # New Year
            return "new_year"
        else:
            return "regular"
    
    def get_time_of_day(self, timestamp: int) -> str:
        """Determine time of day from timestamp."""
        dt = datetime.fromtimestamp(timestamp / 1000)
        hour = dt.hour
        
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def get_day_of_week(self, timestamp: int) -> str:
        """Get day of week from timestamp."""
        dt = datetime.fromtimestamp(timestamp / 1000)
        return dt.strftime("%A")
    
    def create_signature_from_current_state(
        self,
        error_code: str,
        issuer: str,
        payment_method: str,
        failure_rate: float,
        timestamp: int
    ) -> IncidentSignature:
        """Create incident signature from current state."""
        return IncidentSignature(
            error_code=error_code,
            issuer=issuer,
            payment_method=payment_method,
            failure_rate=failure_rate,
            time_of_day=self.get_time_of_day(timestamp),
            day_of_week=self.get_day_of_week(timestamp),
            season=self.get_seasonal_context(timestamp)
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            "total_incidents": len(self.incidents),
            "successful_resolutions": sum(1 for i in self.incidents if i.success),
            "avg_resolution_time": sum(i.resolution_time_minutes for i in self.incidents) / len(self.incidents) if self.incidents else 0,
            "unique_error_codes": len(set(i.signature.error_code for i in self.incidents)),
            "unique_issuers": len(set(i.signature.issuer for i in self.incidents))
        }
