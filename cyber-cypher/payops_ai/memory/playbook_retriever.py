"""RAG-based playbook retrieval using Google Gemini."""

import logging
import json
from typing import List, Dict, Any, Optional
import requests

from payops_ai.memory.incident_store import HistoricalIncident, IncidentSignature

logger = logging.getLogger(__name__)


class PlaybookRetriever:
    """Retrieves operational playbooks using RAG with Gemini."""
    
    def __init__(self, api_key: str):
        """Initialize playbook retriever.
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    def retrieve_playbook(
        self,
        current_signature: IncidentSignature,
        similar_incidents: List[tuple[HistoricalIncident, float]],
        current_telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retrieve operational playbook using RAG.
        
        Args:
            current_signature: Current incident signature
            similar_incidents: List of similar historical incidents
            current_telemetry: Current system telemetry
            
        Returns:
            Playbook with recommended actions
        """
        if not similar_incidents:
            return self._generate_default_playbook(current_signature)
        
        # Build context from historical incidents
        context = self._build_context(similar_incidents, current_telemetry)
        
        # Generate playbook using Gemini
        try:
            playbook = self._query_gemini(current_signature, context, current_telemetry)
            return playbook
        except Exception as e:
            logger.error(f"Failed to retrieve playbook from Gemini: {e}")
            return self._generate_fallback_playbook(similar_incidents[0][0])
    
    def _build_context(
        self,
        similar_incidents: List[tuple[HistoricalIncident, float]],
        current_telemetry: Dict[str, Any]
    ) -> str:
        """Build context from historical incidents."""
        context_parts = []
        
        context_parts.append("=== HISTORICAL INCIDENTS (Most Similar First) ===\n")
        
        for i, (incident, similarity) in enumerate(similar_incidents, 1):
            context_parts.append(f"\n--- Incident {i} (Similarity: {similarity:.0%}) ---")
            context_parts.append(f"ID: {incident.incident_id}")
            context_parts.append(f"When: {incident.signature.day_of_week} {incident.signature.time_of_day}, {incident.signature.season}")
            context_parts.append(f"Problem: {incident.description}")
            context_parts.append(f"Error: {incident.signature.error_code}")
            context_parts.append(f"Issuer: {incident.signature.issuer}")
            context_parts.append(f"Method: {incident.signature.payment_method}")
            context_parts.append(f"Failure Rate: {incident.signature.failure_rate:.0%}")
            context_parts.append(f"\nIntervention: {incident.intervention_taken}")
            context_parts.append(f"Outcome: {incident.outcome}")
            context_parts.append(f"Success: {'Yes' if incident.success else 'No'}")
            context_parts.append(f"Resolution Time: {incident.resolution_time_minutes} minutes")
            
            if incident.lessons_learned:
                context_parts.append("\nLessons Learned:")
                for lesson in incident.lessons_learned:
                    context_parts.append(f"  • {lesson}")
            
            if incident.telemetry:
                context_parts.append("\nTelemetry:")
                for key, value in incident.telemetry.items():
                    context_parts.append(f"  • {key}: {value}")
        
        return "\n".join(context_parts)
    
    def _query_gemini(
        self,
        current_signature: IncidentSignature,
        historical_context: str,
        current_telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query Gemini for playbook recommendation."""
        
        prompt = f"""You are an expert payment operations AI analyzing a current incident.

CURRENT INCIDENT:
- Error Code: {current_signature.error_code}
- Issuer: {current_signature.issuer}
- Payment Method: {current_signature.payment_method}
- Failure Rate: {current_signature.failure_rate:.0%}
- Time Context: {current_signature.day_of_week} {current_signature.time_of_day}
- Season: {current_signature.season}

CURRENT TELEMETRY:
{json.dumps(current_telemetry, indent=2)}

{historical_context}

Based on the historical incidents above, provide a detailed operational playbook for the current incident.

Your response must be in JSON format with these fields:
{{
  "recommended_action": "primary action to take (suppress_path, reduce_retry_attempts, reroute_traffic, or alert_ops)",
  "confidence": 0.0-1.0,
  "reasoning": "why this action based on historical patterns",
  "expected_outcome": "what we expect to happen",
  "estimated_resolution_minutes": number,
  "key_learnings_applied": ["list of relevant lessons from history"],
  "risk_factors": ["potential risks to watch for"],
  "rollback_plan": "how to rollback if this doesn't work",
  "monitoring_metrics": ["metrics to watch during intervention"]
}}

Respond ONLY with valid JSON, no other text."""

        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        url = f"{self.gemini_url}?key={self.api_key}"
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract text from Gemini response
        if "candidates" in result and len(result["candidates"]) > 0:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Parse JSON from response
            # Remove markdown code blocks if present
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            playbook = json.loads(text)
            return playbook
        else:
            raise Exception("No response from Gemini")
    
    def _generate_default_playbook(self, signature: IncidentSignature) -> Dict[str, Any]:
        """Generate default playbook when no similar incidents found."""
        return {
            "recommended_action": "alert_ops",
            "confidence": 0.3,
            "reasoning": "No similar historical incidents found. Alerting operations team for manual review.",
            "expected_outcome": "Operations team will investigate and determine appropriate action",
            "estimated_resolution_minutes": 30,
            "key_learnings_applied": [],
            "risk_factors": ["Unknown incident pattern", "No historical precedent"],
            "rollback_plan": "N/A - observation only",
            "monitoring_metrics": ["failure_rate", "latency_p95", "retry_count"]
        }
    
    def _generate_fallback_playbook(self, incident: HistoricalIncident) -> Dict[str, Any]:
        """Generate fallback playbook from most similar incident."""
        return {
            "recommended_action": incident.intervention_taken,
            "confidence": 0.7,
            "reasoning": f"Based on similar incident {incident.incident_id}: {incident.description}",
            "expected_outcome": incident.outcome,
            "estimated_resolution_minutes": incident.resolution_time_minutes,
            "key_learnings_applied": incident.lessons_learned,
            "risk_factors": ["API call failed, using cached playbook"],
            "rollback_plan": "Monitor for 5 minutes, rollback if no improvement",
            "monitoring_metrics": ["failure_rate", "latency_p95", "success_rate"]
        }
