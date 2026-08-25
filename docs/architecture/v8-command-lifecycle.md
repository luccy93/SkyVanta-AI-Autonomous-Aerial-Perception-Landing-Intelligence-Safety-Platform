# SkyVanta AI — Volume 8 Command Lifecycle Specification

---

## 1. Lifecycle State Machine

Every high-level `FlightCommand` undergoes a deterministic state machine progression from creation to completion or termination:

```
                  +---------------+
                  |    CREATED    |
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |   VALIDATED   | -------> [ REJECTED / EXPIRED ]
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |  AUTHORIZED   | -------> [ REJECTED / UNSAFE ]
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |     SENT      | -------> [ TIMEOUT / BUSY ]
                  +-------+-------+
                          |
                          v
                  +---------------+
                  | ACKNOWLEDGED  |
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |   EXECUTING   | -------> [ CANCELLED / FAILED ]
                  +-------+-------+
                          |
                          v
                  +---------------+
                  |   COMPLETED   |
                  +---------------+
```

---

## 2. Transition Rules and Guard Conditions

1. **`CREATED` $\to$ `VALIDATED`**: Structural integrity, finite numerical parameters, valid sequence number, and valid timestamp within clock skew tolerance.
2. **`VALIDATED` $\to$ `AUTHORIZED`**: Command source is authorized; progression commands (`DESCEND`, etc.) have explicit V7 safety clearance (`is_safe_for_progression == True`); flight mode is compatible.
3. **`AUTHORIZED` $\to$ `SENT`**: Rate limit verified and sequence uniqueness recorded.
4. **`SENT` $\to$ `ACKNOWLEDGED`**: Autopilot returns a valid `CommandAcknowledgement` within `ack_timeout_sec` (default: 0.5s).
5. **`ACKNOWLEDGED` $\to$ `EXECUTING`**: Autopilot begins physical/simulated execution of the directive.
6. **`EXECUTING` $\to$ `COMPLETED`**: Target altitude reached or landing touchdown verified.
7. **`CANCELLED`**: An incoming higher-priority command (e.g. `ABORT`) preempts active execution.
8. **`TIMEOUT`**: Autopilot fails to acknowledge or complete within configured watchdog windows.
