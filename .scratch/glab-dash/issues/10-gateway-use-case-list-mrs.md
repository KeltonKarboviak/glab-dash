# 10 — Gateway + use case: list MRs for a project section

**What to build:** given a resolved token and a project-scoped `Section`,
fetch that project's merge requests from gitlab.com via python-gitlab,
filtered by `state`, and return them as Domain MR entities. The GitLab base
URL is a single named constant (e.g. `GITLAB_COM_URL`) defined where the
python-gitlab client is constructed, passed as a parameter into gateway
construction rather than referenced as a literal at each call site.
Application's use case depends only on Domain plus a gateway interface
(protocol) it defines — never concrete Infrastructure. No TUI in this
ticket; verified via fakes/fixtures and a demo script or test that prints
the filtered MR entities for a real or fixture-backed project.

**Blocked by:** 08 — Credential resolution, 09 — Config loading & section schema.

Status: complete

- [x] `GITLAB_COM_URL` constant lives in Infrastructure and is the only place gitlab.com's URL is spelled out
- [x] Infrastructure gateway implementation lists a project's MRs via python-gitlab and maps them into Domain MR entities
- [x] Application use case depends only on Domain + a gateway protocol, tested against a fake gateway seeded with canned entities
- [x] `state` filter (`opened`/`closed`/`merged`/`all`) is applied via a pure Domain filter function
- [x] A demo script or test shows the use case returning correctly filtered MRs for a project section
