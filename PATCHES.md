# Quantum dashboard patches on the pinned Hermes

**Upstream source:** `NousResearch/hermes-agent`
**Pin:** `d923a5eb487a17c0a68801bba9ef0f56c81040a8` (Release 0.22.2)
**Fork:** `bondrider/hermes-agent`, branch `quantum/dashboard-patches-001`.

Small, separate patches that fix live Hermes dashboard faults. Each is one commit so it rebases
cleanly onto a future upstream pin.

---

## Patch A - the dashboard adopts the gateway that owns its OWN home (APPLIED, home-scoped)

**Symptom:** the dashboard gateway badge reads "Stopped / mode none / no pid" while the gateway
runs and serves the chats.

**Root cause:** the container entrypoint starts and supervises `hermes gateway run` itself (folded
on with `--force`, sometimes with no `gateway.pid`); the dashboard status route's own liveness
verdict can miss it. **Live fact (2026-10-27):** the dashboard's `hermes_home` is the DEVELOPMENT
home (`/data/hermes/dev`) and the badge must show THAT home's gateway (pid 691) - not the default
home.

**Fix (home-scoped):**
- `gateway/host_topology.py` - pure helper `adopt_home_gateway_when_stopped(running, pid, home, *, probe=None)`.
  When, and only when, the local verdict is not-running, it proves the gateway that owns `home`
  through `gateway.status.live_gateway_pid_for_home` (pid file + runtime lock, then the runtime
  record proven against the live process - the launch-service / no-`gateway.pid` case included) and
  reports running with that home's pid. A gateway in a DIFFERENT home is never adopted.
- `hermes_cli/web_routers/status.py` - `_resolve_gateway_status` passes the dashboard's OWN resolved
  home (`profile_dir or get_process_hermes_home()`) to the helper and overlays the result at its
  return (guarded; `gateway_state` -> `running` only on adoption).
- `tests/gateway/test_host_gateway_adoption.py` - the helper: adopts the gateway owning this home;
  a gateway in a different home is NOT adopted; a running verdict is untouched (probe skipped); the
  default probe resolves `live_gateway_pid_for_home`.

**Re-apply on a new upstream:** re-add the helper and re-wire the one overlay at the
`_resolve_gateway_status` return, passing the surface's own home. Guarded, so default behaviour is
unchanged when no gateway owns the home.

**Tests:** the full pytest suite needs Python 3.11+ (image build / CI). On this host the helper's
assertions were run directly and pass; the TS/py gates run in CI.

---

## Patch B - the picker offers only the models a route can serve (quantum-tracker, separate PR)

NOT a fork patch. `provider.only` is not an inventory-visible field and names the OpenRouter serving
provider (e.g. `atlas-cloud/fp8`), which does not map to a model-id prefix, so `hermes_cli/inventory.py`
cannot filter on it. Each route's custom provider carries no `models:` list, so the picker
aggregator-lists the whole catalogue. **Clean fix (config-side):** in quantum-tracker
`infra/quantum-hermes/entrypoint.sh`, the `custom_providers` builder adds `"models": [e["model"]]`
per route, so each custom provider offers only its one served model. Delivered as a separate
quantum-tracker PR (branch `hermes/picker-provider-models`) with a test.

---

## Patch C - chat websocket 1005 at ~35 s (DROPPED)

Live diagnosis (2026-10-27): the ~35 s close was NOT real. No keep-alive is built. gate.py already
imposes no idle close and the client pings every 15 s.

---

## Patch D — DROPPED (not needed on v0.22.2)

The senior re-review confirmed (Carril 75d4d9de) that v0.22.2's dashboard agent builder ALREADY
applies `agent.disabled_toolsets`: `_make_agent` passes `disabled_toolsets=_load_disabled_toolsets()`,
`_background_agent_kwargs` (inherited by the preview agent via `_ephemeral_preview_agent_kwargs`)
passes it, and `_with_session_toolsets` already subtracts it from the client-surface fold-in. So with
PR 714's complement seed — which disables `project` and `desktop_ui` per profile — the project tools
are already removed from every advisory chat on v0.22.2. No code patch is applied; this branch is
Patch A only. The real-path guard test `infra/quantum-hermes/tests/test_profile_tui_toolsets.sh`
(carried by the re-pin PR) stays and MUST pass with NO patch on the merged-714 main.
