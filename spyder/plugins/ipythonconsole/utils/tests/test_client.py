# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for the kernel client."""

# Standard library imports
from unittest.mock import Mock

# Third-party imports
from jupyter_client.threaded import IOLoopThread, ThreadedKernelClient

# Local imports
from spyder.plugins.ipythonconsole.utils.client import SpyderKernelClient


def test_stop_channels_closes_streams_before_client_teardown(monkeypatch):
    """ZMQ streams are closed before their sockets are destroyed."""
    calls = []
    client = SpyderKernelClient()

    ioloop_thread = IOLoopThread()
    monkeypatch.setattr(ioloop_thread, "is_alive", lambda: True)
    client.ioloop_thread = ioloop_thread

    for channel_name in [
        "_shell_channel",
        "_iopub_channel",
        "_stdin_channel",
        "_control_channel",
    ]:
        channel = Mock()
        channel.close.side_effect = (
            lambda channel_name=channel_name: calls.append(channel_name)
        )
        setattr(client, channel_name, channel)

    monkeypatch.setattr(
        ThreadedKernelClient,
        "stop_channels",
        lambda self: calls.append("client_teardown"),
    )

    client.stop_channels()

    assert calls == [
        "_shell_channel",
        "_iopub_channel",
        "_stdin_channel",
        "_control_channel",
        "client_teardown",
    ]
