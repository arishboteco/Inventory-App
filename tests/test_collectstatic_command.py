import subprocess
from unittest import mock

from django.core.management import call_command
from django.contrib.staticfiles.management.commands import collectstatic as base_collectstatic


def test_collectstatic_runs_npm_build(monkeypatch):
    monkeypatch.setattr(
        "core.management.commands.collectstatic.which",
        lambda cmd: "/usr/bin/npm" if cmd == "npm" else None,
    )
    run_calls = []

    def fake_run(cmd, check):
        run_calls.append(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)

    def dummy_handle(self, *args, **kwargs):
        return

    monkeypatch.setattr(base_collectstatic.Command, "handle", dummy_handle)

    call_command("collectstatic", verbosity=0, interactive=False)

    assert ["npm", "run", "build"] in run_calls


def test_collectstatic_skips_when_no_package_manager(monkeypatch):
    monkeypatch.setattr("core.management.commands.collectstatic.which", lambda cmd: None)
    run_mock = mock.Mock()
    monkeypatch.setattr(subprocess, "run", run_mock)

    def dummy_handle(self, *args, **kwargs):
        return

    monkeypatch.setattr(base_collectstatic.Command, "handle", dummy_handle)

    call_command("collectstatic", verbosity=0, interactive=False)

    run_mock.assert_not_called()
