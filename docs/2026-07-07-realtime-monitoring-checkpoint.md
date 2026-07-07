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

## Database Guard

A heartbeat stability migration prevents older collectors or skewed endpoint
clocks from moving an asset heartbeat timestamp backward after a fresher
heartbeat has already been stored.

## Login Latency

Login activity polling now runs on a shorter cadence, and lock or unlock
fallback detection is invoked from the same path that already observes Windows
Lock Screen transitions.

## Active Application Sync

The user-session active application agent now refreshes heartbeat state and
invokes session fallback detection during foreground polling, keeping timeline
and login activity updates aligned.

## Unlock Refresh

When an unlock or reconnect event is recorded, the monitoring agent immediately
samples the foreground application and stores a fresh telemetry event instead of
waiting for a later application change.

## Login Summary

Dashboard login summaries now select the latest successful login using the
maximum login timestamp and use narrower deduplication so real unlock events are
not hidden as duplicates.
