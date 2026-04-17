#!/usr/bin/env python3
"""
SSH soak test — simulates N concurrent agent-like SSH clients to stress the shell
server and trigger the intermittent hang.

Each client:
  - Connects with password auth and terminal type "moo-automation"
  - Sends "look" every SEND_INTERVAL seconds
  - On connection loss, logs the timestamp and reconnects after RECONNECT_DELAY seconds
  - Tracks per-agent connect/fail counts

Usage:
    uv run python extras/tools/ssh_soak_test.py \
        --host localhost --port 8022 \
        --user <username> --password <password> \
        --agents 6

Ctrl-C to stop; prints a summary on exit.
"""

import argparse
import asyncio
import datetime
import sys

import asyncssh


SEND_INTERVAL = 5.0  # seconds between commands
RECONNECT_DELAY = 2.0  # seconds to wait before reconnecting after a drop

_stats: dict[int, dict] = {}


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


async def run_agent(agent_id: int, host: str, port: int, user: str, password: str, stop: asyncio.Event) -> None:
    stats = _stats[agent_id] = {"connects": 0, "drops": 0, "last_drop": None}

    while not stop.is_set():
        try:
            async with asyncssh.connect(
                host,
                port=port,
                username=user,
                password=password,
                known_hosts=None,
                term_type="moo-automation",
                request_pty=True,
            ) as conn:
                stats["connects"] += 1
                print(f"[{_ts()}] agent-{agent_id} connected (total connects: {stats['connects']})")
                async with conn.create_process(request_pty=True, term_type="moo-automation") as proc:
                    while not stop.is_set():
                        try:
                            proc.stdin.write("look\n")
                            await asyncio.sleep(SEND_INTERVAL)
                        except (asyncssh.DisconnectError, asyncssh.ConnectionLost, BrokenPipeError, OSError):
                            break
        except asyncssh.ConnectionLost as e:
            stats["drops"] += 1
            stats["last_drop"] = _ts()
            print(f"[{_ts()}] agent-{agent_id} DROPPED (ConnectionLost: {e}) — reconnecting in {RECONNECT_DELAY}s")
        except asyncssh.DisconnectError as e:
            stats["drops"] += 1
            stats["last_drop"] = _ts()
            print(f"[{_ts()}] agent-{agent_id} DROPPED (DisconnectError: {e}) — reconnecting in {RECONNECT_DELAY}s")
        except Exception as e:  # pylint: disable=broad-exception-caught
            stats["drops"] += 1
            stats["last_drop"] = _ts()
            print(f"[{_ts()}] agent-{agent_id} ERROR ({type(e).__name__}: {e}) — reconnecting in {RECONNECT_DELAY}s")

        if not stop.is_set():
            await asyncio.sleep(RECONNECT_DELAY)

    print(f"[{_ts()}] agent-{agent_id} stopped")


async def main() -> None:
    parser = argparse.ArgumentParser(description="SSH soak test for moo_shell")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8022)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--agents", type=int, default=6)
    args = parser.parse_args()

    print(f"Starting {args.agents} agent(s) → {args.host}:{args.port} as '{args.user}'")
    print("Press Ctrl-C to stop.\n")

    stop = asyncio.Event()
    tasks = [
        asyncio.create_task(run_agent(i, args.host, args.port, args.user, args.password, stop))
        for i in range(args.agents)
    ]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        stop.set()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    print("\n--- Summary ---")
    for i in range(args.agents):
        s = _stats.get(i, {})
        print(
            f"  agent-{i}: connects={s.get('connects', 0)}  drops={s.get('drops', 0)}  last_drop={s.get('last_drop')}"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
