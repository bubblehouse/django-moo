#!/usr/bin/env python3
"""
SSH server watchdog — polls the shell health endpoint (port 8023) every PROBE_INTERVAL
seconds and auto-recovers on failure.

On each failure:
  1. Sends SIGUSR1 to the moo_shell process inside the container to dump asyncio state
  2. Waits LOG_FLUSH_DELAY seconds for logs to flush
  3. Saves the last 120s of shell logs to ssh_hang_incidents/<timestamp>.log
  4. Restarts the shell container
  5. Resets the clean-run counter

Tracks consecutive clean seconds. Exits with success message when GOAL_SECONDS (3600)
is reached without a hang.

Usage:
    cd /path/to/django-moo
    uv run python extras/tools/ssh_watchdog.py [--health-host HOST] [--health-port PORT]

Ctrl-C to stop.
"""

import argparse
import asyncio
import datetime
import os
import socket
import subprocess
import sys

PROBE_INTERVAL = 10  # seconds between health checks
PROBE_TIMEOUT = 3  # seconds before a probe is considered failed
LOG_FLUSH_DELAY = 3  # seconds to wait after SIGUSR1 before capturing logs
GOAL_SECONDS = 3600  # declare victory after this many consecutive clean seconds
INCIDENT_DIR = "ssh_hang_incidents"


def _ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _probe(host: str, port: int) -> bool:
    """Return True if port answers within PROBE_TIMEOUT seconds."""
    try:
        with socket.create_connection((host, port), timeout=PROBE_TIMEOUT) as s:
            s.recv(16)
        return True
    except OSError:
        return False


def _run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True, check=False)


def _capture_incident(timestamp: str) -> str:
    os.makedirs(INCIDENT_DIR, exist_ok=True)
    log_path = os.path.join(INCIDENT_DIR, f"{timestamp}.log")

    # SIGUSR1 → faulthandler Python stack dump (works even if event loop is blocked)
    # SIGUSR2 → asyncio task list (requires event loop to process the signal)
    # Target only the python process running moo_shell, not pgrep or the parent shell
    for sig in ("USR1", "USR2"):
        result = _run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "shell",
                "sh",
                "-c",
                f"for pid in $(pgrep -f 'manage.py moo_shell'); do kill -{sig} $pid 2>/dev/null; done",
            ],
            capture=True,
        )
        print(f"  SIG{sig} sent: rc={result.returncode}")

    import time

    time.sleep(LOG_FLUSH_DELAY)

    # Capture last 120s of logs
    logs = _run(
        ["docker", "compose", "logs", "shell", "--since", "120s"],
        capture=True,
    )
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"# Incident captured at {timestamp}\n\n")
        f.write(logs.stdout)
        f.write(logs.stderr)

    print(f"  Saved {len(logs.stdout)} bytes to {log_path}")
    return log_path


def _restart_shell() -> None:
    print("  Restarting shell container...")
    _run(["docker", "compose", "restart", "shell"])
    print("  Restart issued.")


def _append_index(timestamp: str, log_path: str) -> None:
    index_path = os.path.join(INCIDENT_DIR, "index.log")
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp}  {log_path}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="SSH shell server watchdog")
    parser.add_argument("--health-host", default="localhost")
    parser.add_argument("--health-port", type=int, default=8023)
    args = parser.parse_args()

    print(f"Watchdog started — probing {args.health_host}:{args.health_port} every {PROBE_INTERVAL}s")
    print(f"Goal: {GOAL_SECONDS}s ({GOAL_SECONDS // 60} minutes) without a hang")
    print(f"Incidents saved to: {INCIDENT_DIR}/\n")

    clean_seconds = 0
    incident_count = 0

    try:
        while True:
            ok = _probe(args.health_host, args.health_port)

            if ok:
                clean_seconds += PROBE_INTERVAL
                if clean_seconds % 60 == 0:
                    print(f"[{_ts()}] healthy — {clean_seconds}s clean ({clean_seconds // 60}m)")
                if clean_seconds >= GOAL_SECONDS:
                    print(f"\n[{_ts()}] SUCCESS: {GOAL_SECONDS}s without a hang. Bug appears fixed.")
                    sys.exit(0)
            else:
                incident_count += 1
                timestamp = _ts()
                print(f"[{timestamp}] HANG DETECTED (incident #{incident_count}, was clean for {clean_seconds}s)")
                log_path = _capture_incident(timestamp)
                _append_index(timestamp, log_path)
                _restart_shell()
                # Wait for the container to come back up before probing again
                import time

                time.sleep(25)
                clean_seconds = 0
                print(f"[{_ts()}] Resuming health checks after restart\n")

            import time

            time.sleep(PROBE_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n[{_ts()}] Watchdog stopped. Incidents: {incident_count}, last clean streak: {clean_seconds}s")
        sys.exit(0)


if __name__ == "__main__":
    main()
