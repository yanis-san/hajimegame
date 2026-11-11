"""Load test: N rooms of M bots play real games against a separate server process.

    uv run --project apps/server python tools/loadtest.py --rooms 200 --players 6

Starts uvicorn as a subprocess (so server CPU/RSS are measured in isolation), plays complete games over real
websockets, then reports the server-side message processing p95 (from Prometheus histogram buckets), client
round-trip latency, server memory growth and game completion. Exit code 1 if a target is missed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import psutil
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = ROOT / "apps" / "server"
sys.path.insert(0, str(SERVER_DIR))

from app.japanese.dictionary import Dictionary  # noqa: E402
from app.japanese.kana import fragment_ngrams  # noqa: E402
from app.japanese.levels import LEVEL_MAX_RANK  # noqa: E402

ORIGIN = "http://localhost:5173"
LEVEL = "n4"


def build_candidates(dictionary: Dictionary) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for entry_id in range(len(dictionary)):
        entry = dictionary.entry(entry_id)
        if entry.rank > LEVEL_MAX_RANK[LEVEL]:
            continue
        for reading in entry.readings:
            for gram in fragment_ngrams(reading):
                bucket = out.setdefault(gram, [])
                if len(bucket) < 40:
                    bucket.append(reading)
    return out


def http_json(url: str, method: str = "GET") -> dict[str, object]:
    request = urllib.request.Request(
        url,
        method=method,
        data=b"" if method == "POST" else None,
        headers={"Origin": ORIGIN, "X-Hajime-Client": "web", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        return json.loads(response.read())  # type: ignore[no-any-return]


def histogram_quantile(metrics: str, name: str, q: float) -> float:
    buckets: list[tuple[float, float]] = []
    for line in metrics.splitlines():
        m = re.match(rf'{name}_bucket\{{le="([^"]+)"\}} ([0-9.e+]+)', line)
        if m:
            buckets.append((float("inf") if m.group(1) == "+Inf" else float(m.group(1)), float(m.group(2))))
    buckets.sort()
    total = buckets[-1][1]
    if total == 0:
        return 0.0
    target = q * total
    for bound, count in buckets:
        if count >= target:
            return bound
    return float("inf")


class Bot:
    def __init__(self, port: int, code: str, name: str, candidates: dict[str, list[str]], rng: random.Random) -> None:
        self.url = f"ws://127.0.0.1:{port}/ws/{code}"
        self.code = code
        self.name = name
        self.candidates = candidates
        self.rng = rng
        self.rtts: list[float] = []
        self.finished = False
        self.errors: list[str] = []
        self.player_id = ""
        self.is_host = False
        self.ws = None
        self.used: set[str] = set()
        self.sent_at: float | None = None

    async def run(self, ready: asyncio.Event, start: asyncio.Event) -> None:
        async with connect(self.url, origin=ORIGIN, max_queue=None) as ws:
            await ws.send(json.dumps({"t": "join", "room": self.code, "name": self.name}))
            pinger = asyncio.get_running_loop().create_task(self.ping_forever(ws))
            async for raw in ws:
                msg = json.loads(raw)
                tag = msg["t"]
                if tag == "welcome":
                    self.player_id = msg["player_id"]
                elif tag == "snapshot":
                    # The host is whoever joined first, not necessarily Bot0.
                    ready.set()
                    asyncio.get_running_loop().create_task(self.begin(ws, start, msg["host"] == msg["you"]))
                elif tag == "turn" and msg["player_id"] == self.player_id:
                    asyncio.get_running_loop().create_task(self.play(ws, msg["fragment"]))
                elif tag in ("accepted", "rejected") and self.sent_at is not None:
                    if tag == "rejected" or msg["player_id"] == self.player_id:
                        self.rtts.append(time.perf_counter() - self.sent_at)
                        self.sent_at = None
                elif tag == "error":
                    self.errors.append(msg["code"])
                elif tag == "game_over":
                    self.finished = True
                    pinger.cancel()
                    return

    async def begin(self, ws: object, start: asyncio.Event, host: bool) -> None:
        send = ws.send  # type: ignore[attr-defined]
        if not host:
            await send(json.dumps({"t": "ready", "ready": True}))
            return
        await start.wait()
        await send(json.dumps({"t": "settings", "lives": 1, "fuse_seconds": 5}))
        await asyncio.sleep(0.5)
        await send(json.dumps({"t": "start"}))

    async def ping_forever(self, ws: object) -> None:
        """Real clients ping every few seconds for clock sync; that also keeps the heartbeat satisfied."""
        n = 0
        while True:
            await asyncio.sleep(5)
            n += 1
            await ws.send(json.dumps({"t": "ping", "n": n, "t0": time.time()}))  # type: ignore[attr-defined]

    async def play(self, ws: object, fragment: str) -> None:
        # 70% answer in 0.2-1.5 s with a real word, 30% let the bomb explode
        if self.rng.random() > 0.7:
            return
        await asyncio.sleep(0.2 + self.rng.random() * 1.3)
        words = [w for w in self.candidates.get(fragment, []) if w not in self.used]
        if not words:
            return
        word = self.rng.choice(words)
        self.used.add(word)
        self.sent_at = time.perf_counter()
        try:
            await ws.send(json.dumps({"t": "submit", "text": word}))  # type: ignore[attr-defined]
        except Exception:
            self.sent_at = None


async def play_room(
    port: int, players: int, candidates: dict[str, list[str]], seed: int, delay: float = 0.0
) -> list[Bot]:
    await asyncio.sleep(delay)
    code = str(http_json(f"http://127.0.0.1:{port}/api/rooms", "POST")["code"])
    rng = random.Random(seed)
    start = asyncio.Event()
    bots = [Bot(port, code, f"Bot{i}", candidates, random.Random(rng.random())) for i in range(players)]
    ready_events = [asyncio.Event() for _ in bots]
    tasks = [asyncio.create_task(b.run(r, start)) for b, r in zip(bots, ready_events, strict=True)]
    await asyncio.wait_for(asyncio.gather(*(r.wait() for r in ready_events)), timeout=60)
    await asyncio.sleep(1.0)
    start.set()
    try:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=240)
    except TimeoutError:
        info = http_json(f"http://127.0.0.1:{port}/api/rooms/{code}")
        detail = [(b.name, b.finished, b.errors) for b in bots]
        raise RuntimeError(f"room {code} did not finish: server says {info}; bots {detail}") from None
    return bots


async def main_async(args: argparse.Namespace) -> int:
    dictionary = Dictionary.load()
    candidates = build_candidates(dictionary)
    env = {
        **os.environ,
        "HAJIME_MAX_ROOMS_PER_IP": "100000",
        "HAJIME_JOIN_ATTEMPTS_PER_MINUTE": "1000000",
        "HAJIME_ROOM_CREATIONS_PER_MINUTE": "1000000",
        "HAJIME_COUNTDOWN_SECONDS": "1",
        "PYTHONUTF8": "1",
        "HAJIME_ENV": "prod-load",
    }
    port = args.port
    server = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory", "--port", str(port), "--log-level", "warning"],
        cwd=SERVER_DIR,
        env=env,
    )
    try:
        for _ in range(200):
            try:
                http_json(f"http://127.0.0.1:{port}/readyz")
                break
            except Exception:
                await asyncio.sleep(0.25)
        else:
            print("server did not start")
            return 1
        launcher = psutil.Process(server.pid)

        def rss_mb() -> float:
            # On Windows the venv python is a launcher that spawns the real interpreter as a child.
            procs = [launcher, *launcher.children(recursive=True)]
            return sum(p.memory_info().rss for p in procs) / 1e6

        rss_start = rss_mb()
        samples: list[float] = []

        async def sample_memory() -> None:
            while True:
                samples.append(rss_mb())
                await asyncio.sleep(2)

        sampler = asyncio.create_task(sample_memory())
        started = time.perf_counter()
        wave_rss: list[float] = []
        results: list[list[Bot] | BaseException] = []
        for wave in range(args.waves):
            results = await asyncio.gather(
                *(
                    play_room(port, args.players, candidates, wave * 10_000 + seed, random.Random(seed).random() * args.ramp)
                    for seed in range(args.rooms)
                ),
                return_exceptions=True,
            )
            await asyncio.sleep(4)  # let rooms close and the allocator settle
            wave_rss.append(round(rss_mb(), 1))
        elapsed = time.perf_counter() - started
        sampler.cancel()
        failed = [r for r in results if isinstance(r, BaseException)]
        bots = [b for r in results if not isinstance(r, BaseException) for b in r]
        finished_rooms = sum(1 for r in results if not isinstance(r, BaseException) and all(b.finished for b in r))
        metrics = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=10).read().decode()  # noqa: S310
        p95 = histogram_quantile(metrics, "hajime_message_processing_seconds", 0.95)
        p50 = histogram_quantile(metrics, "hajime_message_processing_seconds", 0.50)
        lag_p95 = histogram_quantile(metrics, "hajime_event_loop_lag_seconds", 0.95)
        lag_p99 = histogram_quantile(metrics, "hajime_event_loop_lag_seconds", 0.99)
        handle_p95 = histogram_quantile(metrics, "hajime_room_handle_seconds", 0.95)
        handle_p99 = histogram_quantile(metrics, "hajime_room_handle_seconds", 0.99)
        rtts = [x for b in bots for x in b.rtts]
        rss_end = rss_mb()
        tail = samples[len(samples) // 2 :] or [rss_end]
        report = {
            "rooms": args.rooms,
            "players_per_room": args.players,
            "connections": args.rooms * args.players,
            "finished_rooms": finished_rooms,
            "failed_rooms": len(failed),
            "failures": [f"{type(f).__name__}: {f}" for f in failed][:5],
            "duration_s": round(elapsed, 1),
            "server_processing_p50_ms": p50 * 1000,
            "server_processing_p95_ms": p95 * 1000,
            "loop_lag_p95_ms": lag_p95 * 1000,
            "loop_lag_p99_ms": lag_p99 * 1000,
            "room_handle_p95_ms": handle_p95 * 1000,
            "room_handle_p99_ms": handle_p99 * 1000,
            "client_send_p95_ms": round(sorted(rtts)[int(len(rtts) * 0.95)] * 1000, 2) if rtts else None,
            "rss_start_mb": round(rss_start, 1),
            "rss_peak_mb": round(max(samples or [rss_end]), 1),
            "rss_end_mb": round(rss_end, 1),
            "rss_late_mean_mb": round(statistics.mean(tail), 1),
            "rss_after_each_wave_mb": wave_rss,
            "errors": sorted({e for b in bots for e in b.errors}),
        }
        print(json.dumps(report, indent=2))
        leak = len(wave_rss) > 1 and wave_rss[-1] - wave_rss[0] > max(30.0, 0.1 * (wave_rss[0] - rss_start))
        print("memory: " + ("GROWING between waves" if leak else "stable between waves"))
        ok = finished_rooms == args.rooms and p95 <= 0.05 and not leak
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        server.terminate()
        server.wait(timeout=15)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rooms", type=int, default=200)
    parser.add_argument("--players", type=int, default=6)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--waves", type=int, default=2, help="repeat the whole load to detect leaks")
    parser.add_argument("--ramp", type=float, default=10.0, help="spread room starts over this many seconds")
    sys.exit(asyncio.run(main_async(parser.parse_args())))


if __name__ == "__main__":
    main()
