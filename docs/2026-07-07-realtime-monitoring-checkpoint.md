# Asset Sentinel Realtime Monitoring Checkpoint

## Scope

This checkpoint captures the realtime monitoring fixes for heartbeat stability,
lock and unlock detection latency, active application synchronization, and login
activity freshness across monitored Windows endpoints.

## Heartbeat Stability

Heartbeat writes now use the database receive time as the shared source of truth
for fleet online status. Dashboard status calculations use the same reference
clock so endpoint clock skew does not cause false offline flicker.

## Offline Grace

The heartbeat offline grace window is set to tolerate normal network latency,
database round trips, and short Windows scheduler pauses during lock and unlock
without hiding genuinely stale devices.
