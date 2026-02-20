import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorPolicy:
    severity: str = "error"   # info|warn|error|critical
    mode: str = "continue"    # continue|degrade|fatal
    max_retries: int = 0
    backoff_s: float = 0.0


POLICIES = {
    "startup.load_env": ErrorPolicy(severity="critical", mode="fatal"),
    "startup.osc_client": ErrorPolicy(severity="critical", mode="fatal", max_retries=1, backoff_s=0.25),
    "startup.controls": ErrorPolicy(severity="critical", mode="fatal"),
    "startup.wait_xr18": ErrorPolicy(severity="critical", mode="fatal", max_retries=2, backoff_s=0.5),
    "startup.initial_sync": ErrorPolicy(severity="critical", mode="fatal", max_retries=1, backoff_s=0.25),
    "startup.channel_names": ErrorPolicy(severity="warn", mode="continue"),
    "loop.sync": ErrorPolicy(severity="error", mode="degrade", max_retries=2, backoff_s=0.15),
    "loop.poll": ErrorPolicy(severity="warn", mode="continue", max_retries=1, backoff_s=0.05),
    "loop.render": ErrorPolicy(severity="warn", mode="continue"),
    "loop.apply.write": ErrorPolicy(severity="error", mode="continue", max_retries=1, backoff_s=0.05),
    "loop.display_health": ErrorPolicy(severity="warn", mode="degrade"),
}


def get_policy(where: str) -> ErrorPolicy:
    return POLICIES.get(where, ErrorPolicy())


def sleep_backoff(policy: ErrorPolicy, attempt: int):
    if policy.backoff_s <= 0:
        return
    time.sleep(policy.backoff_s * max(1, attempt + 1))
