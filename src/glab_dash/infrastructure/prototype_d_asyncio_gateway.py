"""PROTOTYPE D -- throwaway. Do not import from production code.

Question: does hand-rolling an asyncio HTTP client (httpx.AsyncClient)
around GitLab's REST + GraphQL APIs get bootup meaningfully closer to the
<=1s target than the thread-pool/GraphQL winner (perf/enrichment-trimmed-
thread-pool, 7-9s)? python-gitlab is sync-only, so this fetches the MR list
via paginated REST pages issued concurrently, and the GraphQL enrichment
chunks (currently sequential in gitlab_gateway.py's _graphql_enrich)
concurrently too, both via asyncio.gather.

See benchmark_prototype_d.py to run it against a live group.
"""

import asyncio
from typing import Any

import httpx

_GRAPHQL_PROJECTS_PER_REQUEST = 8

_ENRICHMENT_QUERY_TEMPLATE = """
query({variable_declarations}) {{
{project_queries}
}}
"""

_PROJECT_QUERY_TEMPLATE = """
  {alias}: project(fullPath: ${path_var}) {{
    mergeRequests(iids: ${iids_var}) {{
      nodes {{
        iid
        approvedBy {{ nodes {{ username }} }}
        approvalsLeft
        diffStatsSummary {{ additions deletions }}
      }}
    }}
  }}"""


async def _fetch_first_page(
    client: httpx.AsyncClient, path: str, params: dict[str, Any]
) -> tuple[list[dict], int]:
    response = await client.get(path, params={**params, "page": 1})
    response.raise_for_status()
    total_pages = int(response.headers.get("x-total-pages", "1"))
    return response.json(), total_pages


async def _fetch_page(
    client: httpx.AsyncClient, path: str, params: dict[str, Any], page: int
) -> list[dict]:
    response = await client.get(path, params={**params, "page": page})
    response.raise_for_status()
    return response.json()


async def fetch_group_merge_requests_async(
    client: httpx.AsyncClient, group: str, *, state: str = "all"
) -> list[dict]:
    """All pages of a group's MR list, fetched concurrently instead of
    python-gitlab's sequential page-by-page REST pagination.
    """
    path = f"/api/v4/groups/{group.replace('/', '%2F')}/merge_requests"
    params = {"per_page": 100, "state": state} if state != "all" else {"per_page": 100}
    first_page, total_pages = await _fetch_first_page(client, path, params)
    if total_pages <= 1:
        return first_page
    rest = await asyncio.gather(
        *(_fetch_page(client, path, params, page) for page in range(2, total_pages + 1))
    )
    all_pages = [first_page, *rest]
    return [mr for page in all_pages for mr in page]


def _group_by_project(raw_mrs: list[dict]) -> dict[str, list[dict]]:
    by_project: dict[str, list[dict]] = {}
    for raw_mr in raw_mrs:
        project = raw_mr["references"]["full"].rsplit("!", 1)[0]
        by_project.setdefault(project, []).append(raw_mr)
    return by_project


async def _enrich_chunk(
    client: httpx.AsyncClient, chunk: dict[str, list[dict]]
) -> dict[tuple[str, int], tuple[int, int, int, int]]:
    variable_declarations = []
    project_queries = []
    variables: dict[str, Any] = {}
    aliases_by_project: dict[str, str] = {}
    for index, (project, project_mrs) in enumerate(chunk.items()):
        alias, path_var, iids_var = f"p{index}", f"path{index}", f"iids{index}"
        aliases_by_project[project] = alias
        variable_declarations.append(f"${path_var}: ID!, ${iids_var}: [String!]")
        project_queries.append(
            _PROJECT_QUERY_TEMPLATE.format(alias=alias, path_var=path_var, iids_var=iids_var)
        )
        variables[path_var] = project
        variables[iids_var] = [str(raw_mr["iid"]) for raw_mr in project_mrs]

    response = await client.post(
        "/api/graphql",
        json={
            "query": _ENRICHMENT_QUERY_TEMPLATE.format(
                variable_declarations=", ".join(variable_declarations),
                project_queries="\n".join(project_queries),
            ),
            "variables": variables,
        },
    )
    response.raise_for_status()
    data = response.json()["data"]

    enrichment: dict[tuple[str, int], tuple[int, int, int, int]] = {}
    for project, alias in aliases_by_project.items():
        project_data = data.get(alias)
        if project_data is None:
            continue
        for node in project_data["mergeRequests"]["nodes"]:
            approvals_given = len(node["approvedBy"]["nodes"])
            approvals_required = approvals_given + node["approvalsLeft"]
            enrichment[(project, int(node["iid"]))] = (
                approvals_given,
                approvals_required,
                node["diffStatsSummary"]["additions"],
                node["diffStatsSummary"]["deletions"],
            )
    return enrichment


async def graphql_enrich_async(
    client: httpx.AsyncClient, raw_mrs: list[dict]
) -> dict[tuple[str, int], tuple[int, int, int, int]]:
    """Every GraphQL enrichment chunk fired concurrently instead of the
    sequential for-loop in gitlab_gateway.py's _graphql_enrich.
    """
    by_project = _group_by_project(raw_mrs)
    projects = list(by_project.items())
    chunks = [
        dict(projects[start : start + _GRAPHQL_PROJECTS_PER_REQUEST])
        for start in range(0, len(projects), _GRAPHQL_PROJECTS_PER_REQUEST)
    ]
    results = await asyncio.gather(*(_enrich_chunk(client, chunk) for chunk in chunks))
    enrichment: dict[tuple[str, int], tuple[int, int, int, int]] = {}
    for result in results:
        enrichment.update(result)
    return enrichment


async def _rest_enrich_one(
    client: httpx.AsyncClient, project: str, iid: int
) -> tuple[tuple[str, int], tuple[int, int, int, int]]:
    """Same 2 REST calls/MR the pre-GraphQL sync gateway made
    (approvals.get, changes), just issued concurrently instead of
    thread-pool-batched.
    """
    encoded_project = project.replace("/", "%2F")
    approvals_response, changes_response = await asyncio.gather(
        client.get(f"/api/v4/projects/{encoded_project}/merge_requests/{iid}/approvals"),
        client.get(f"/api/v4/projects/{encoded_project}/merge_requests/{iid}/changes"),
    )
    approvals_response.raise_for_status()
    changes_response.raise_for_status()
    approvals = approvals_response.json()
    changes = changes_response.json()
    additions = sum(_count_diff_lines(c["diff"], "+") for c in changes.get("changes", []))
    deletions = sum(_count_diff_lines(c["diff"], "-") for c in changes.get("changes", []))
    return (project, iid), (
        len(approvals.get("approved_by", [])),
        approvals.get("approvals_required", 0),
        additions,
        deletions,
    )


def _count_diff_lines(diff: str, prefix: str) -> int:
    return sum(
        1
        for line in diff.splitlines()
        if line.startswith(prefix) and not line.startswith(prefix * 3)
    )


async def rest_enrich_async(
    client: httpx.AsyncClient, raw_mrs: list[dict]
) -> dict[tuple[str, int], tuple[int, int, int, int]]:
    """Pure-REST asyncio enrichment: no GraphQL at all, just every MR's
    2 REST calls fired concurrently via asyncio.gather.
    """
    by_project = _group_by_project(raw_mrs)
    pairs = [
        (project, raw_mr["iid"]) for project, project_mrs in by_project.items() for raw_mr in project_mrs
    ]
    results = await asyncio.gather(*(_rest_enrich_one(client, project, iid) for project, iid in pairs))
    return dict(results)


async def list_group_merge_requests_async(
    base_url: str, token: str, group: str, *, state: str = "all", strategy: str = "graphql"
) -> tuple[list[dict], dict[tuple[str, int], tuple[int, int, int, int]]]:
    async with httpx.AsyncClient(
        base_url=base_url, headers={"Authorization": f"Bearer {token}"}, timeout=30
    ) as client:
        raw_mrs = await fetch_group_merge_requests_async(client, group, state=state)
        if strategy == "rest":
            enrichment = await rest_enrich_async(client, raw_mrs)
        else:
            enrichment = await graphql_enrich_async(client, raw_mrs)
        return raw_mrs, enrichment
