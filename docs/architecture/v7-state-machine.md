# SkyVanta AI — Volume 7 Landing State Machine Specification

---

## 1. Operational Phases

```
               +---------------+
               |     IDLE      |
               +-------+-------+
                       |
                       v
               +---------------+
               |   SEARCHING   | <-------------------------+
               +-------+-------+                           |
                       | Target Detected                   |
                       v                                   |
               +---------------+                           |
               |TARGET_ACQUIRED|                           |
               +-------+-------+                           |
                       |                                   |
                       v                                   |
               +---------------+                           |
               |   ALIGNING    |                           |
               +-------+-------+                           |
                       | Aligned (Offset < 1.5m, Yaw < 15°) |
                       v                                   |
               +---------------+                           |
               |  APPROACHING  |                           |
               +-------+-------+                           |
                       | Approach Envelope Verified        |
                       v                                   |
               +---------------+                           |
               |   DESCENDING  |                           |
               +-------+-------+                           |
                       | Final Altitude (< 1.5m)           |
                       v                                   |
               +---------------+                           |
               | FINAL_APPROACH|                           |
               +-------+-------+                           |
                       | Touchdown Verified (N >= 10 Frames)
                       v                                   |
               +---------------+                           |
               |LANDING_CONFIRM|                           |
               +---------------+                           |
                                                           |
+-------------------------------------------------------+  |
|                 SAFETY OVERRIDE STATES                |  |
|                                                       |  |
|      +---------------+       +---------------+        |  |
|      |   ABORTING    | ----> |   RECOVERY    | -------+  |
|      +---------------+       +-------+-------+           |
|                                      | Timeout           |
|                                      v                   |
|                              +---------------+           |
|                              |     FAULT     | (Terminal)|
|                              +---------------+           |
+-------------------------------------------------------+--+
```

---

## 2. Phase Semantics

1. **`IDLE`**: Standby state; no landing sequence active.
2. **`SEARCHING`**: Actively sweeping visual field to detect landing fiducials.
3. **`TARGET_ACQUIRED`**: Target detected; verifying track stability and pose quality.
4. **`ALIGNING`**: Maneuvering to bring body-relative lateral and heading offsets within descent bounds.
5. **`APPROACHING`**: Verifying dynamic speed and descent corridor limits prior to altitude reduction.
6. **`DESCENDING`**: Controlled vertical descent while continuously tracking pad geometry.
7. **`FINAL_APPROACH`**: Close-proximity regime ($< 1.5\text{ m}$) requiring tightened precision tolerances.
8. **`LANDING_CONFIRMED`**: Touchdown conditions persistently verified across multiple consecutive frames.
9. **`ABORTING`**: Safety breach detected; immediate cessation of descent.
10. **`RECOVERY`**: Executing climb-out and attempting target re-acquisition.
11. **`FAULT`**: Terminal latched fault state due to unrecoverable sensor failure or timeout.
