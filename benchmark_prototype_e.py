"""PROTOTYPE E benchmark -- throwaway. Run: uv run python benchmark_prototype_e.py

Single group-level GraphQL query (list fields + approvals + diff stats in
one connection, cursor-paginated) instead of A-D's per-project-aliased
chunking. See .scratch/mr-enrichment-bootup-perf/issues/01-prototype-e-group-level-graphql.md
"""

import argparse
import os
import time

import requests

GROUP = "ramsey-solutions/data-platform"

_QUERY = """
query($path: ID!, $after: String) {
  group(fullPath: $path) {
    mergeRequests(state: opened, first: 100, includeSubgroups: true, after: $after) {
      pageInfo { hasNextPage endCursor }
      count
      nodes {
        iid
        title
        state
        author { username }
        assignees { nodes { username } }
        labels { nodes { title } }
        sourceBranch
        targetBranch
        webUrl
        updatedAt
        approvedBy { nodes { username } }
        approvalsLeft
        diffStatsSummary { additions deletions }
        project { fullPath }
      }
    }
  }
}
"""


def fetch_all(token: str) -> tuple[int, float]:
    """One-or-few-page group-level fetch. Returns (mr_count, elapsed_seconds)."""
    start = time.perf_counter()
    after = None
    total = 0
    while True:
        response = requests.post(
            "https://gitlab.com/api/graphql",
            json={"query": _QUERY, "variables": {"path": GROUP, "after": after}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if "errors" in payload:
            raise RuntimeError(payload["errors"])
        connection = payload["data"]["group"]["mergeRequests"]
        total += len(connection["nodes"])
        if not connection["pageInfo"]["hasNextPage"]:
            break
        after = connection["pageInfo"]["endCursor"]
    return total, time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    token = os.environ["GITLAB_TOKEN"]

    times = []
    for i in range(args.repeat):
        count, elapsed = fetch_all(token)
        print(f"run {i}: {elapsed:.2f}s, {count} MRs")
        times.append(elapsed)

    fastest = min(times)
    print()
    print(f"fastest: {fastest:.2f}s")
    print(f"<=1s target: {'MET' if fastest <= 1 else 'NOT MET'}")


if __name__ == "__main__":
    main()
