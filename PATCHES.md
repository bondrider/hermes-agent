# Quantum dashboard patches on the pinned Hermes

**Upstream source:** `NousResearch/hermes-agent`
**Pin:** `d923a5eb487a17c0a68801bba9ef0f56c81040a8` (Release 0.22.2)
**Fork:** `bondrider/hermes-agent`, branch `quantum/dashboard-patches-001`.

These are small, separate patches that fix three live Hermes dashboard faults. Each is a single
commit so it rebases cleanly onto a future upstream pin. Keep them minimal and re-appliable.

---

## Patch A — the dashboard adopts the one live host gateway (APPLIED)

**Symptom:** the dashboard gateway badge reads "Stopped / mode none / no pid" while the gateway
runs and serves the chats.

**Root cause:** the entrypoint starts and supervises `hermes gateway run` itself (folded on with
`--force`); the dashboard status route's per-home liveness proof does not recognise that process.
v0.22.2 already has the authoritative answer in `gateway/host_topology.py:host_gateway_topology()`
(proven-live, `_from_host_record` -> `_from_served_record`), but no dashboard surface called it.

**Files:**
- `gateway/host_topology.py` — new pure helper `adopt_host_gateway_when_stopped(running, pid, *, probe=None)`.
- `hermes_cli/web_routers/status.py` — `_resolve_gateway_status` overlays the helper at its return (guarded).
- `tests/gateway/test_host_gateway_adoption.py` — unit test of the helper.

**Re-apply:** re-add the helper and re-wire the one overlay at the `_resolve_gateway_status`
return. The overlay is guarded, so default behaviour is unchanged when no host gateway is proven.

**Still needs the live dashboard:** `host_gateway_topology()` reads the DEFAULT home's record,
while the dashboard is served over the development home. José's live dashboard must confirm the
badge flips to the intended gateway's pid. If the development-home gateway must be adopted instead,
the helper call should pass a home-scoped probe (a `live_gateway_pid_for_home(dev_home)` variant) —
decide after the live check.

---

## Patch B — the picker offers only the models a route can serve (REDIRECTED to quantum-tracker)

**NOT a fork patch.** The intended "filter the inventory catalogue by `provider.only`" is not
implementable in `hermes_cli/inventory.py`:

1. `provider.only` is **not** an inventory-visible field. In the Quantum config each route is a
   custom provider `{name, base_url, key_env, extra_body:{provider:{only:[vendor]}}}` with **no
   `models:` list**, so the picker treats it as an OpenRouter routing aggregator and lists the whole
   catalogue (`hermes_cli/inventory.py` aggregator path).
2. `provider.only` names the OpenRouter **serving provider** (e.g. `nvidia`, `atlas-cloud/fp8`),
   which does **not** map to a model-id vendor prefix (e.g. the `openrouter-dots` route pins
   `atlas-cloud/fp8` but its model is `dots-studio/dots-3-note-preview:free`). So an inventory
   filter keyed on `provider.only` cannot select the right models.

**Clean fix (config-side, in quantum-tracker):** in `infra/quantum-hermes/entrypoint.sh`, the
`custom_providers` builder should add an explicit `"models": [e["model"]]` to each route's entry.
Each route serves exactly its one model; an explicit `models:` allow-list makes the provider
`is_user_defined` so the picker offers only that model — directly "only the models the provider can
serve". Add a seed/inventory test that each custom provider carries its single route model.

This belongs in a quantum-tracker PR (the Dockerfile re-pin PR or a sibling), not in this fork.

---

## Patch C — chat websocket 1005 at ~35 s (DEFERRED, needs the live dashboard)

**Finding:** the quantum-tracker wrapper gate (`infra/quantum-hermes/gate/gate.py:1001 _relay`)
imposes **no** ~35 s idle close (`up.settimeout(None)`, a 3600 s cap, a 5 s select poll), and the
web client already pings every 15 s (`apps/shared/src/json-rpc-channel.ts:154`
`DEFAULT_HEARTBEAT_INTERVAL_MS=15_000`, deadline 45 s). So the ~35 s 1005 is the **edge/proxy**
closing a socket that lacks sub-35 s frames — most plausibly the chat/stream ws, distinct from the
15 s-pinged control channel.

**Decide after the live diagnosis (which socket gets the 1005):**
- if the stream ws — a server-initiated keep-alive ping under 35 s in `tui_gateway/ws.py`
  (`handle_ws`), config-gated; a fork patch, unit-testable with a fake clock; **or**
- if purely the edge — raise the Railway service websocket/idle timeout (outside both repos).

gate.py is ruled out as the fix site.
