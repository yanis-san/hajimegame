# 0002 Fuse driven by a corrected server deadline

Status: accepted. The server sends `deadline` in its own monotonic milliseconds. Each client estimates its offset
from 8 pings (median of the lowest-RTT half, NTP style) and keeps pinging every 5 s. The fuse is a WAAPI animation
started at `fuse - remaining`, re-synchronised when the estimate drifts more than 60 ms. No network traffic per
frame. Tested in `clock.spec.ts` (error under 100 ms with realistic jitter).
