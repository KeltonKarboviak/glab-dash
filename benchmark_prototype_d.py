"""PROTOTYPE D benchmark -- throwaway. Run: uv run python benchmark_prototype_d.py

Compares two hand-rolled asyncio httpx strategies for the same live group's
MR list + enrichment (the state this repo boots the TUI with -- see
~/.config/glab-dash/config.yml):

- graphql: async REST list fetch + concurrent batched-alias GraphQL
  enrichment chunks (prototype_d_asyncio_gateway.graphql_enrich_async)
- rest: async REST list fetch + concurrent pure-REST per-MR enrichment,
  no GraphQL at all (prototype_d_asyncio_gateway.rest_enrich_async)

The prior sync thread-pool/GraphQL baseline (perf/enrichment-trimmed-
thread-pool, 7-9s) is not re-run here against the full "state: all"
history -- that took long enough the user killed it. Defaults to
state=opened to keep this feasible; pass --state=all to reproduce the full
historical fetch.
"""

import argparse
import asyncio
import os
import time

from glab_dash.infrastructure.gitlab_gateway import GITLAB_COM_URL
from glab_dash.infrastructure.prototype_d_asyncio_gateway import list_group_merge_requests_async

GROUP = "ramsey-solutions/data-platform"


async def run(token: str, state: str, strategy: str) -> float:
    start = time.perf_counter()
    raw_mrs, enrichment = await list_group_merge_requests_async(
        GITLAB_COM_URL, token, GROUP, state=state, strategy=strategy
    )
    elapsed = time.perf_counter() - start
    print(f"{strategy:8s}: {elapsed:.2f}s, {len(raw_mrs)} MRs, {len(enrichment)} enriched")
    return elapsed


async def main_async(token: str, state: str) -> None:
    graphql_s = await run(token, state, "graphql")
    rest_s = await run(token, state, "rest")
    print()
    print(f"graphql:     {graphql_s:.2f}s")
    print(f"rest:        {rest_s:.2f}s")
    print(f"speedup:     {rest_s / graphql_s:.2f}x (graphql vs rest)")
    fastest = min(graphql_s, rest_s)
    print(f"<=1s target: {'MET' if fastest <= 1 else 'NOT MET'} (fastest={fastest:.2f}s)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="opened", choices=["opened", "closed", "merged", "all"])
    args = parser.parse_args()
    token = os.environ["GITLAB_TOKEN"]
    asyncio.run(main_async(token, args.state))


if __name__ == "__main__":
    main()
