from unittest.mock import Mock

from jupyter_client.threaded import IOLoopThread
from qtconsole.client import QtKernelClient

from spyder.plugins.ipythonconsole.utils.client import SpyderKernelClient


def test_client_stops_callbacks_and_drains_before_dependency_teardown(
    monkeypatch,
):
    """Pending channel events finish before dependency-owned teardown."""
    events = []
    client = SpyderKernelClient()
    client.ioloop_thread = IOLoopThread()
    client.ioloop_thread.start()

    channel_names = ["shell", "iopub", "stdin", "control"]
    channels = []
    for channel_name in channel_names:
        channel = Mock()

        def stop_receiving(_callback, name=channel_name):
            events.append(f"stop_receiving_{name}")
            client.ioloop.add_callback(
                lambda name=name: events.append(f"pending_event_{name}")
            )

        channel.stream.on_recv.side_effect = stop_receiving
        channel.close.side_effect = (
            lambda name=channel_name: events.append(f"close_{name}")
        )
        channels.append(channel)

    (
        client._shell_channel,
        client._iopub_channel,
        client._stdin_channel,
        client._control_channel,
    ) = channels

    def dependency_stop_channels(_client):
        for channel in channels:
            channel.close()
        events.append("teardown")

    monkeypatch.setattr(
        QtKernelClient,
        "stop_channels",
        dependency_stop_channels,
    )

    try:
        client.stop_channels()
    finally:
        client.ioloop_thread.stop()

    for channel_name in channel_names:
        assert events.index(f"stop_receiving_{channel_name}") < events.index(
            f"pending_event_{channel_name}"
        )
        assert events.index(f"pending_event_{channel_name}") < events.index(
            f"close_{channel_name}"
        )
        assert events.index(f"close_{channel_name}") < events.index("teardown")
        assert events.count(f"close_{channel_name}") == 1
