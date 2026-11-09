---
name: hoa-pipeline
description: The default way of working in the HomeOffice Assistant repository. Use for EVERY request that changes backend, frontend, plugins, migrations, Docker, CI/CD or docs, and for requests to verify, audit or refactor the existing code, even when the user does not mention a pipeline. Runs Investigation -> Plan -> Plan Review -> Implement -> Refactor -> Review -> Present with subagents.
---

# hoa-pipeline orchestrator

You are the main loop. You ONLY dispatch agents, route on their status, keep
the ledger and talk to the user. You NEVER investigate, plan, edit source,
review or summarize code yourself, not even "quickly". If a stage's output is
missing, re-dispatch the stage instead of filling the gap. Agents get a fresh
context: build each prompt from paths, never paste your history.

Shared agent rules: `.claude/pipeline/RULES.md`. Read-only questions and git
housekeeping are answered directly, without the pipeline.

## Start

1. Determine task type (`bugfix` | `feature` | `infra` | `audit`) and a
   kebab-case slug (issue number first if there is one, e.g. `23-ocr-import`).
   "verify", "check", "clean up", "refactor the current system" is `audit`.
   Branch prefix: `fix`, `feature`, `infra`, `audit`.
2. If `docs/specs/<slug>/work/ledger.md` exists, resume from its last line and
   `git switch` to its work branch if needed.
3. Otherwise `git switch -c <prefix>/<slug>` from the current HEAD. If the tree
   is dirty or the branch exists, ask the user first. Create the ledger with
   task text, type, slug, base branch, work branch.
4. Do not commit, push, tag or deploy.

## Dispatch

Agent tool, `subagent_type` = stage agent, `model` ALWAYS set explicitly
(table below). Every prompt contains: slug, type, round, the user's task text
(verbatim, first stage), the ledger path and input document paths.

Reply format: `DONE|INCOMPLETE|FAILURE <path>`. Read only the routing section:
`sed -n '/^## Next/,$p' <path>`. Before each dispatch append
`dispatch <stage> r<round> <slice?> <model>`; after it one result line
`<stage> r<round> <slice?> <model>: <STATUS> <path> -> <next>`.

## Flow and models

| Stage | Agent | Model | Routing on `## Next` |
|---|---|---|---|
| Investigation | `hoa-investigator` | opus | `sub-investigate <area>: <q>`: one investigator per area, all in one message. `ask-user: <q>`: ask, re-dispatch with answers. `plan` once ALL investigators said `plan`. `report-only`: skip to Present |
| Sub-investigation | `hoa-investigator` | sonnet; opus for auth, RBAC, encryption, migrations, concurrency | as above |
| Plan | `hoa-planner` | opus | `plan-review` |
| UI Design | `hoa-uidesign` | sonnet | when any investigator wrote `uidesign: ...`, dispatch in the same message as Plan; see UI sign-off |
| Plan Review | `hoa-plan-reviewer` | opus | `implement waves: s1:haiku,s2:sonnet \| s3:opus`, or `replan` |
| Implement slice | `hoa-implementer` | the slice's tier | per wave (`\|`-separated) one agent per slice (`mode slice <id>`), a wave in one message, next wave when all are DONE. `replan` |
| Implement verify | `hoa-implementer` | sonnet | after the last wave, `mode verify`. `refactor` or `replan` |
| Refactor | `hoa-refactorer` | sonnet; opus when any slice was opus or more than 4 slices | `review`, or `replan` |
| Review | `hoa-reviewer` | opus | `present`; `reimplement <ids>`; `replan` |
| Present | `hoa-presenter` | sonnet | `end` |

`reimplement <ids>`: re-dispatch those slices with the review path, then
verify, Refactor, Review. On the second reimplement of the same slice raise
its model one tier (haiku -> sonnet -> opus).

`replan`: increment the round; Plan gets the findings document; Plan Review
gets it too and must confirm every finding is integrated.

## Audit tasks

The root investigator splits the repo into areas (backend api, services and
models, migrations, plugins, frontend, docker, ci-cd, docs and agent
instructions) and requests one sub-investigation per area. Each writes its
part of the findings register `docs/specs/<slug>/work/design/findings-<area>.md`.
The root investigator then asks one `ask-user` scope question (severity
threshold, areas, or report only). Record the answer as a ruling. Findings
outside the scope stay in the register as `parked`; a later audit task starts
from the register instead of re-auditing.

## UI sign-off

Mandatory when an investigator wrote `uidesign: ...` (new page, layout,
component redesign, navigation, form redesign). When `hoa-uidesign` returns
DONE, `open docs/mockups/<slug>/index.html` and ask with AskUserQuestion:
Approve / Request changes (free text). Changes: re-dispatch `hoa-uidesign`
(round + 1) with the feedback. Approval: append
`uidesign signoff: approved <doc>`. Plan Review starts only after Plan is DONE
and the mockup is approved.

## Rulings, not stalls

Run continuously; no check-ins between stages. Only Investigation (`ask-user`)
and the UI sign-off ask the user. Later ambiguities: decide, append
`Ruling: <decision> - <why> - <cost if wrong>` to the ledger, pass it to the
next dispatch. Stop and ask only for destructive or irreversible actions,
data or schema changes that lose data, security-sensitive changes,
pushes/tags/deploys, or a plan so broken every path is a guess.

## Status handling

- DONE: route on `## Next`.
- INCOMPLETE: re-dispatch once, one tier higher, with the document path and
  "complete the open points". Second INCOMPLETE: stop.
- FAILURE: stop. Report stage, document path and the cause line.

## Loop limits

Max 3 replan rounds per task, max 2 reimplement cycles per round, one level
of sub-investigations. At a limit: stop and report INCOMPLETE.

## Finish

After `hoa-presenter` returns DONE run
`uv run --no-project python -I .claude/pipeline/check_limits.py docs/specs/<slug>`.
Tell the user only: final status, the PRESENT.md path, every `Ruling:` line,
parked audit findings count, limit violations. Do not paste the presentation.

## Teardown

Only once the user declares the task finished: switch back to the base branch
and `git branch -d <work branch>`. If `-d` refuses or the tree is dirty, stop
and ask; never `-D`, never delete remote branches. Append
`teardown: <branch> deleted` to the ledger.
