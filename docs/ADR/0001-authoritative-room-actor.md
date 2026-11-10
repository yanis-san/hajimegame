# 0001 Authoritative server, one actor per room

Status: accepted. The server decides every word, turn, deadline and life. A room is one asyncio task draining a
single queue (client messages, disconnects, timers), so there are no races and a deadline tie is decided by the receive
timestamp (`at <= deadline` wins). The browser sends intents only. Cost: a room lives in one process; scaling out needs
routing by room code (ADR 0003).
