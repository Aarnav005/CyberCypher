# Implementation Plan: Continuous Payment Stream

## Overview

Implement a continuous payment stream simulation with stochastic drift, emergent behaviors, and closed-loop feedback. This replaces scenario-based testing with realistic streaming data where failures emerge naturally from parameter drift.

## Tasks

- [x] 1. Create Stochastic Drift Engine
  - Implement Ornstein-Uhlenbeck process for parameter drift
  - Support per-issuer state (success_rate, latency_ms, retry_prob)
  - Implement parameter bounds clipping
  - Add configurable drift parameters (θ, σ, μ)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [ ]* 1.1 Write property test for parameter bounds preservation
  - **Property 1: Parameter Bounds Preservation**
  - **Validates: Requirements 2.4**

- [ ]* 1.2 Write property test for mean reversion
  - **Property 7: Drift Mean Reversion**
  - **Validates: Requirements 2.1, 2.6**

- [x] 2. Create Continuous Payment Generator
  - Implement continuous transaction generation at configurable rate
  - Create circular buffer for recent transactions (maxsize=1000)
  - Implement weighted issuer selection based on volume multipliers
  - Generate outcomes based on current drift parameters
  - Use wall-clock timestamps for transactions
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ]* 2.1 Write property test for time monotonicity
  - **Property 6: Time Monotonicity**
  - **Validates: Requirements 1.3, 7.4**

- [ ]* 2.2 Write property test for buffer overflow handling
  - **Property 5: Buffer Overflow Handling**
  - **Validates: Requirements 10.2**

- [x] 3. Create Feedback Controller
  - Track active interventions with start/end times
  - Implement success rate multipliers for suppress_path
  - Implement volume multipliers for suppress_path and reroute_traffic
  - Implement retry multipliers for reduce_retry_attempts
  - Auto-expire interventions after duration
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ]* 3.1 Write property test for intervention effect consistency
  - **Property 2: Intervention Effect Consistency**
  - **Validates: Requirements 4.1**

- [ ]* 3.2 Write property test for feedback loop causality
  - **Property 3: Feedback Loop Causality**
  - **Validates: Requirements 4.5**

- [ ]* 3.3 Write property test for intervention expiration
  - **Property 8: Intervention Expiration**
  - **Validates: Requirements 4.4**

- [x] 4. Integrate with Observation Stream
  - Modify ObservationStream to accept continuous transaction feed
  - Ensure transactions are added to stream in real-time
  - Maintain compatibility with existing agent code
  - _Requirements: 1.1, 6.1, 6.2_

- [x] 5. Create Continuous Agent Loop
  - Implement main loop with configurable cycle interval
  - Generate transactions continuously between cycles
  - Run agent cycle at regular intervals
  - Apply agent decisions to feedback controller
  - Update drift engine each iteration
  - Handle graceful shutdown (SIGINT/SIGTERM)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [ ]* 5.1 Write property test for rolling baseline continuity
  - **Property 4: Rolling Baseline Continuity**
  - **Validates: Requirements 5.2, 5.3**

- [x] 6. Add Configuration Management
  - Create YAML/JSON config file format
  - Load drift parameters (θ, σ, μ)
  - Load per-issuer initial states
  - Load generator parameters (rate, buffer_size)
  - Load agent parameters (cycle_interval, window_duration)
  - Load simulation parameters (time_scale, duration)
  - Validate all parameters
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 7. Implement Time Controller
  - Support real-time mode (1x speed)
  - Support accelerated modes (10x, 100x, 1000x)
  - Scale all time-dependent parameters in accelerated mode
  - Provide current simulation time to all components
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 8. Create Monitoring Dashboard
  - Display current issuer health states
  - Display rolling baseline statistics
  - Display active interventions
  - Display agent cycle metrics (Z-scores, patterns, decisions)
  - Update display every 1-5 seconds
  - Support logging to file
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 9. Add Error Handling
  - Handle buffer overflow gracefully
  - Handle invalid parameters with clipping
  - Handle cycle timeout with warning
  - Handle state persistence failures
  - Implement graceful shutdown
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 10. Create Demo Script
  - Initialize all components with config
  - Run continuous loop for 10 minutes
  - Log key events (patterns detected, interventions applied)
  - Demonstrate emergent behaviors
  - Show Z-scores increasing during degradation
  - Show interventions affecting future generation
  - _Requirements: All_

- [x] 11. Checkpoint - Ensure all tests pass
  - All 35 tests passing
  - Fixed unicode validation in transaction signal generation
  - Fixed Z-score calculation to use baseline std directly
  - Fixed floating point comparison in anomaly detection

## Notes

- Tasks marked with `*` are optional property-based tests
- Each task references specific requirements for traceability
- Checkpoint ensures incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
