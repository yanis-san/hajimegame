# 0003 RoomRegistry interface, Redis ownership

Status: accepted. `RoomRegistry` maps a room code to the instance that owns it. `MemoryRegistry` is the single
process default; `RedisRegistry` uses `SET NX PX` plus a transactional refresh so exactly one instance owns a code.
A websocket that lands on another instance is denied with HTTP 409 and `fly-replay: instance=<owner>`. Tested with two
instances sharing one (fake) Redis. Rooms are lost if their instance dies: acceptable for short games, and the TTL
frees the codes.
