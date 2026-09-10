# Workflow roles — the review-process role contract

**Policy, not mechanism.** This contract defines the roles the HEDIS review workflow
assumes and what each may do. A host platform's **RBAC module is configured to satisfy
it** — the platform owns users, authentication, group→role mapping, enforcement, and
user-management audit (create/assign-role/disable). It does **not** define these domain
roles. Think of this file the way the rules pack is the source of truth for *what to
look for*: it is the source of truth for *who may do what in the review*.

## Roles

| id | label | may… |
|---|---|---|
| `reviewer` | Reviewer | Abstractor — locate/confirm findings, sign off the first read, escalate. |
| `over_reader` | Over-reader | Independent QA over-read and **blind second read**; plus all reviewer actions. Must differ from the primary signer. |
| `administrator` | Administrator | Manage rules packs, priority config, assignments; all review actions. |
| `auditor` | Auditor | **Read-only** — view findings, audit trail, analytics. No write actions. |

## Permission matrix (action → roles)

| action | reviewer | over_reader | administrator | auditor |
|---|:---:|:---:|:---:|:---:|
| `view` | ✅ | ✅ | ✅ | ✅ |
| `analyze` | ✅ | ✅ | ✅ | — |
| `decide_finding` | ✅ | ✅ | ✅ | — |
| `sign_off` | ✅ | ✅ | ✅ | — |
| `escalate` | ✅ | ✅ | ✅ | — |
| `blind_second_read` ⚖ | — | ✅ | ✅ | — |
| `qa_over_read` ⚖ | — | ✅ | ✅ | — |
| `assign` | — | — | ✅ | — |
| `generate_pack` | — | — | ✅ | — |
| `edit_priority_config` | — | — | ✅ | — |
| `manage_vsd` | — | — | ✅ | — |
| `manage_users` | — | — | ✅ (platform-enforced) | — |

## Separation of duties (⚖)

`blind_second_read` and `qa_over_read` carry an **identity-level** rule that RBAC alone
cannot express — RBAC is role-based, not relationship-based:

> The person doing the QA over-read or the blind second read **must be a different
> individual** than whoever performed the primary sign-off (and its finding decisions).

`roles.py` enforces this via `sod_ok(actor_id, prior_actor_ids)` / `authorize(...)`; the
consuming app passes the primary reviewer's user id as `prior_actor_ids`. This is what
makes the inter-rater metric and the QA over-read *independent* rather than a rubber stamp.

## Mapping to a platform RBAC module

A platform (e.g. PenguinAI) that owns RBAC should **configure to** this contract:

1. **Create a group/role per `id`** above (`reviewer`, `over_reader`, `administrator`,
   `auditor`) and map org users into them. Auth, login, and sessions are the platform's.
2. **Grant each group the actions** from the permission matrix. `can(role, action)` is the
   machine-readable form (`roles.py` / `ROLE_MODEL`) to generate that config from.
3. **Add a separation-of-duties policy** for the `⚖` actions: block a principal from
   over-reading / second-reading a case-measure they themselves signed off. RBAC grants the
   *capability*; the SoD policy enforces the *different-person* constraint per item.
4. **Emit user-management audit** (create user / assign role / disable — requirement A11)
   from the platform's own audit facility into the shared audit trail; the workflow skill
   does not manage users, only names the roles they are assigned.

`can()` / `authorize()` are also usable directly by an app that has no external RBAC yet
(as the reference app does) — the same contract, enforced in-process until a platform takes
over. The role *model* stays here regardless of who enforces it.
