# Design Document: Continuous Payment Stream with Stochastic Drift

## Overview

This design transforms the PayOps-AI agent from scenario-based batch testing to a continuous streaming architecture where payment transactions flow continuously, system parameters drift stochastically, and agent interventions create closed-loop feedback. The system simulates realistic payment infrastructure behavior where failures emerge naturally rather than being explicitly programmed.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Continuous Stream Loop                        │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Stochastic │───▶│   Payment    │───▶│  Transaction │     │
│  │ Drift Engine │    │  Generator   │    │    Buffer    │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         ▲                    ▲                     │            │
│         │                    │                     ▼            │
│         │            ┌───────────────┐    ┌──────────────┐     │
│         │            │   Feedback    │    │    Agent     │     │
│         └────────────│  Controller   │◀───│ Orchestrator │     │
│                      └───────────────┘    └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Stochastic Drift Engine**: Updates issuer health, latency, and retry parameters using Ornstein-Uhlenbeck process
2. **Payment Generator**: Continuously generates transactions based on current parameters
3. **Transaction Buffer**: Circular buffer maintaining recent transactions (last 500-1000)
4. **Agent Orchestrator**: Runs continuous cycles on rolling windows
5. **Feedback Controller**: Applies agent interventions to generation parameters

## Components and Interfaces

### 1. Stochastic Drift Engine

```python
class StochasticDriftEngine:
    """Manages parameter drift using Ornstein-Uhlenbeck process."""
    
    def __init__(self, config: DriftConfig):
        self.issuers: Dict[str, IssuerState] = {}
        self.config = config
        self.time_scale = 1.0  # For accelerated time
    
    def update(self, dt: float) -> None:
        """Update all parameters using stochastic drift.
        
        Ornstein-Uhlenbeck: dx = θ(μ - x)dt + σdW
        - θ: mean reversion strength
        - μ: long-term mean
        - σ: volatility
        - dW: Wiener process (Brownian motion)
        """
        for issuer in self.issuers.values():
            # Update success rate
            drift = self.config.theta * (self.config.mean_success - issuer.success_rate) * dt
            diffusion = self.config.sigma * np.random.normal(0, np.sqrt(dt))
            issuer.success_rate = np.clip(issuer.success_rate + drift + diffusion, 0.0, 1.0)
            
            # Update latency (bounded random walk)
            issuer.latency_ms += np.random.normal(0, 10 * np.sqrt(dt))
            issuer.latency_ms = np.clip(issuer.latency_ms, 50, 2000)
            
            # Update retry probability (with occasional spikes)
            if np.random.random() < 0.01 * dt:  # 1% chance per second
                issuer.retry_prob += 0.2  # Spike
            else:
                issuer.retry_prob *= 0.99  # Decay
            issuer.retry_prob = np.clip(issuer.retry_prob, 0.0, 0.5)
```

### 2. Continuous Payment Generator

```python
class ContinuousPaymentGenerator:
    """Generates payment stream with stochastic parameters."""
    
    def __init__(self, drift_engine: StochasticDriftEngine, 
                 feedback_controller: FeedbackController):
        self.drift_engine = drift_engine
        self.feedback = feedback_controller
        self.transaction_rate = 20  # txns/second
        self.buffer = CircularBuffer(maxsize=1000)
    
    def generate_next_batch(self, dt: float) -> List[TransactionSignal]:
        """Generate transactions for time interval dt."""
        count = int(self.transaction_rate * dt)
        transactions = []
        
        for _ in range(count):
            # Select issuer (with volume adjustments from interventions)
            issuer = self._select_issuer_weighted()
            state = self.drift_engine.issuers[issuer]
            
            # Apply feedback adjustments
            effective_success = state.success_rate * self.feedback.get_success_multiplier(issuer)
            effective_retry = state.retry_prob * self.feedback.get_retry_multiplier()
            
            # Generate outcome based on current parameters
            outcome = self._generate_outcome(effective_success, effective_retry)
            latency = self._generate_latency(state.latency_ms)
            retry_count = self._generate_retries(effective_retry)
            
            txn = TransactionSignal(
                transaction_id=self._generate_id(),
                timestamp=int(time.time() * 1000),
                issuer=issuer,
                outcome=outcome,
                latency_ms=latency,
                retry_count=retry_count,
                # ... other fields
            )
            transactions.append(txn)
        
        self.buffer.extend(transactions)
        return transactions
```

### 3. Feedback Controller

```python
class FeedbackController:
    """Applies agent interventions to generation parameters."""
    
    def __init__(self):
        self.active_interventions: List[ActiveIntervention] = []
    
    def apply_intervention(self, intervention: InterventionOption) -> None:
        """Apply intervention and track its effects."""
        active = ActiveIntervention(
            intervention=intervention,
            start_time=time.time(),
            end_time=time.time() + intervention.parameters.get('duration_ms', 300000) / 1000
        )
        self.active_interventions.append(active)
        logger.info(f"Applied intervention: {intervention.type.value} on {intervention.target}")
    
    def get_success_multiplier(self, issuer: str) -> float:
        """Get success rate multiplier for issuer based on active interventions."""
        multiplier = 1.0
        for active in self.active_interventions:
            if active.intervention.type == InterventionType.SUPPRESS_PATH:
                if f"issuer:{issuer}" == active.intervention.target:
                    # Suppress path reduces success rate (simulates blocking)
                    multiplier *= 0.1  # 90% reduction
        return multiplier
    
    def get_volume_multiplier(self, issuer: str) -> float:
        """Get transaction volume multiplier for issuer."""
        multiplier = 1.0
        for active in self.active_interventions:
            if active.intervention.type == InterventionType.SUPPRESS_PATH:
                if f"issuer:{issuer}" == active.intervention.target:
                    multiplier *= 0.1  # 90% volume reduction
            elif active.intervention.type == InterventionType.REROUTE_TRAFFIC:
                if f"issuer:{issuer}" == active.intervention.target:
                    multiplier *= 0.3  # Route away 70%
        return multiplier
    
    def get_retry_multiplier(self) -> float:
        """Get retry probability multiplier."""
        multiplier = 1.0
        for active in self.active_interventions:
            if active.intervention.type == InterventionType.REDUCE_RETRY_ATTEMPTS:
                multiplier *= 0.5  # 50% reduction
        return multiplier
    
    def update(self, current_time: float) -> None:
        """Remove expired interventions."""
        self.active_interventions = [
            a for a in self.active_interventions 
            if current_time < a.end_time
        ]
```

### 4. Continuous Agent Loop

```python
class ContinuousAgentLoop:
    """Main loop for continuous agent operation."""
    
    def __init__(self, orchestrator: AgentOrchestrator,
                 generator: ContinuousPaymentGenerator,
                 config: LoopConfig):
        self.orchestrator = orchestrator
        self.generator = generator
        self.config = config
        self.running = False
    
    def run(self, duration_seconds: Optional[float] = None) -> None:
        """Run continuous loop."""
        self.running = True
        start_time = time.time()
        last_cycle = start_time
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        logger.info("Starting continuous agent loop...")
        
        while self.running:
            current_time = time.time()
            dt = current_time - last_cycle
            
            # Generate new transactions
            new_txns = self.generator.generate_next_batch(dt)
            
            # Add to observation stream
            for txn in new_txns:
                self.orchestrator.stream.add_transaction(txn)
            
            # Run agent cycle if interval elapsed
            if dt >= self.config.cycle_interval:
                try:
                    decision, explanation = self.orchestrator.execute_cycle()
                    
                    # Apply intervention if decided
                    if decision.should_act and decision.selected_option:
                        self.generator.feedback.apply_intervention(decision.selected_option)
                    
                    last_cycle = current_time
                except Exception as e:
                    logger.error(f"Cycle error: {e}", exc_info=True)
            
            # Update drift engine
            self.generator.drift_engine.update(dt)
            
            # Update feedback controller (expire interventions)
            self.generator.feedback.update(current_time)
            
            # Check duration limit
            if duration_seconds and (current_time - start_time) >= duration_seconds:
                break
            
            # Sleep to control loop rate
            time.sleep(0.1)  # 10 Hz loop
        
        logger.info("Continuous agent loop stopped")
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
```

## Data Models

### IssuerState

```python
@dataclass
class IssuerState:
    """Current state of an issuer."""
    issuer_name: str
    success_rate: float  # 0.0 - 1.0
    latency_ms: float    # 50 - 2000
    retry_prob: float    # 0.0 - 0.5
    last_updated: float  # timestamp
```

### DriftConfig

```python
@dataclass
class DriftConfig:
    """Configuration for stochastic drift."""
    theta: float = 0.1          # Mean reversion strength
    sigma: float = 0.05         # Volatility
    mean_success: float = 0.95  # Long-term mean success rate
    dt: float = 1.0             # Time step (seconds)
```

### ActiveIntervention

```python
@dataclass
class ActiveIntervention:
    """Tracks an active intervention."""
    intervention: InterventionOption
    start_time: float
    end_time: float
    
    def is_active(self, current_time: float) -> bool:
        return current_time < self.end_time
    
    def time_remaining(self, current_time: float) -> float:
        return max(0, self.end_time - current_time)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: Parameter Bounds Preservation
*For any* time step, after drift update, all issuer parameters (success_rate, latency_ms, retry_prob) should remain within their valid bounds.
**Validates: Requirements 2.4**

### Property 2: Intervention Effect Consistency
*For any* active suppress_path intervention on an issuer, the transaction volume for that issuer should be reduced by at least 80%.
**Validates: Requirements 4.1**

### Property 3: Feedback Loop Causality
*For any* intervention applied at time T, the generation parameters should reflect the intervention's effects for all transactions generated after time T.
**Validates: Requirements 4.5**

### Property 4: Rolling Baseline Continuity
*For any* agent cycle, the rolling baseline should incorporate observations from the current cycle without resetting previous history.
**Validates: Requirements 5.2, 5.3**

### Property 5: Buffer Overflow Handling
*For any* transaction generation burst, when the buffer reaches capacity, the oldest transactions should be dropped while maintaining buffer size limit.
**Validates: Requirements 10.2**

### Property 6: Time Monotonicity
*For any* two consecutive transactions in the buffer, the timestamp of the later transaction should be greater than or equal to the earlier transaction.
**Validates: Requirements 1.3, 7.4**

### Property 7: Drift Mean Reversion
*For any* issuer with success_rate below mean_success, over a sufficiently long time period (100+ time steps), the success_rate should trend toward mean_success due to mean reversion.
**Validates: Requirements 2.1, 2.6**

### Property 8: Intervention Expiration
*For any* intervention with duration D, after time D has elapsed, the intervention should no longer affect generation parameters.
**Validates: Requirements 4.4**

## Minimum Action Frequency Mechanism

To ensure the agent demonstrates active monitoring even during stable periods, the decision policy implements a minimum action frequency rule:

```python
class DecisionPolicy:
    """Decision policy with minimum action frequency."""
    
    def __init__(self, ...):
        self.cycles_since_last_action = 0
        self.min_action_frequency_cycles = 6
    
    def make_decision(self, options, beliefs, ...) -> InterventionDecision:
        """Make decision with minimum frequency guarantee."""
        
        # Normal NRV-based decision
        best_option, best_nrv = self._rank_by_nrv(options)
        
        # Check minimum frequency rule
        if self.cycles_since_last_action >= (self.min_action_frequency_cycles - 1):
            # 6th cycle: guarantee action if any options available
            if best_option and best_nrv > float('-inf'):
                logger.info(f"Minimum frequency rule triggered (cycle {self.cycles_since_last_action + 1})")
                self.cycles_since_last_action = 0
                return self._create_action_decision(best_option, best_nrv, 
                    rationale=f"Minimum frequency rule: {best_nrv_details}")
        
        # Normal NRV rule: only act if NRV > 0
        if best_nrv > 0:
            self.cycles_since_last_action = 0
            return self._create_action_decision(best_option, best_nrv)
        else:
            self.cycles_since_last_action += 1
            return self._create_no_action_decision(f"NRV={best_nrv:.2f} <= 0")
```

**Key Design Points:**
- Counter tracks cycles since last action
- On 6th cycle (counter = 5), select best option regardless of NRV
- Action is still situation-dependent (uses actual patterns and NRV ranking)
- Counter resets to 0 after any action
- Logs when minimum frequency rule is triggered

## Error Handling

1. **Buffer Overflow**: Drop oldest transactions, log warning
2. **Invalid Parameters**: Clip to valid range, log warning
3. **Cycle Timeout**: Log warning, continue to next cycle
4. **State Persistence Failure**: Continue with in-memory state, log error
5. **Signal Handling**: Graceful shutdown on SIGINT/SIGTERM

## Testing Strategy

### Unit Tests
- Test Ornstein-Uhlenbeck drift calculation
- Test parameter clipping and bounds
- Test feedback multiplier calculations
- Test intervention expiration logic
- Test circular buffer operations

### Property Tests
- Property 1: Parameter bounds (generate random drift steps, verify bounds)
- Property 2: Intervention effects (apply intervention, verify volume reduction)
- Property 3: Feedback causality (apply intervention, verify all subsequent txns affected)
- Property 4: Baseline continuity (run multiple cycles, verify baseline never resets)
- Property 5: Buffer overflow (generate burst, verify size limit)
- Property 6: Time monotonicity (generate transactions, verify timestamps)
- Property 7: Mean reversion (run long simulation, verify convergence)
- Property 8: Intervention expiration (apply intervention, wait duration, verify removal)

### Integration Tests
- Run 10-minute continuous simulation
- Verify emergent patterns (degradation, outage, retry storm)
- Verify agent detects and responds to patterns
- Verify interventions affect future generation
- Verify Z-scores increase during degradation
- Verify graceful shutdown

## Configuration Example

```yaml
drift:
  theta: 0.1              # Mean reversion strength
  sigma: 0.05             # Volatility
  mean_success: 0.95      # Target success rate
  
issuers:
  HDFC:
    initial_success: 0.95
    initial_latency: 200
    initial_retry_prob: 0.05
  ICICI:
    initial_success: 0.97
    initial_latency: 180
    initial_retry_prob: 0.03
  AXIS:
    initial_success: 0.93
    initial_latency: 220
    initial_retry_prob: 0.07
  SBI:
    initial_success: 0.94
    initial_latency: 210
    initial_retry_prob: 0.06

generator:
  transaction_rate: 20    # txns/second
  buffer_size: 1000
  
agent:
  cycle_interval: 15      # seconds
  window_duration_ms: 300000  # 5 minutes
  
simulation:
  time_scale: 1.0         # 1x = real-time, 10x = accelerated
  duration_seconds: 600   # 10 minutes
```
