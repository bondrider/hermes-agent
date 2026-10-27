"""The dashboard adopts the gateway that owns ITS OWN home, never a different home.

An entrypoint-supervised ``hermes gateway run`` for the dashboard's home (the development home,
``/data/hermes/dev``) serves the chats but can be missed by the surface's own liveness verdict.
``adopt_home_gateway_when_stopped`` adopts a proven-live gateway for THIS home only, and only when
the local verdict is not-running.
"""

from gateway.host_topology import adopt_home_gateway_when_stopped

DEV = "/data/hermes/dev"
OTHER = "/data/hermes"


def _probe_for(home_with_live, pid=691):
    def _p(home):
        return pid if str(home) == home_with_live else None

    return _p


def test_stopped_adopts_the_gateway_owning_this_home():
    assert adopt_home_gateway_when_stopped(False, None, DEV, probe=_probe_for(DEV)) == (True, 691)


def test_a_gateway_in_a_different_home_is_not_adopted():
    assert adopt_home_gateway_when_stopped(False, None, DEV, probe=_probe_for(OTHER)) == (False, None)


def test_running_local_is_untouched_and_probe_not_consulted():
    calls = []

    def _p(home):
        calls.append(home)
        return 691

    assert adopt_home_gateway_when_stopped(True, 17, DEV, probe=_p) == (True, 17)
    assert calls == []  # a running gateway is never overridden; the probe is skipped


def test_default_probe_resolves_live_gateway_pid_for_home(monkeypatch):
    import gateway.status as gs

    monkeypatch.setattr(gs, "live_gateway_pid_for_home", lambda home: 691 if str(home) == DEV else None)
    assert adopt_home_gateway_when_stopped(False, None, DEV) == (True, 691)
