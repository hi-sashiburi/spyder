# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for the IPython console main widget."""

# Standard library imports
from types import SimpleNamespace
from unittest.mock import Mock

# Local imports
from spyder.plugins.ipythonconsole.utils.kernel_handler import KernelHandler
from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget,
)


def test_close_all_clients_shuts_down_related_kernels(mocker):
    """All related clients should stop their threads when Spyder closes."""
    clients = [
        SimpleNamespace(connection_file="kernel.json", close_client=Mock()),
        SimpleNamespace(connection_file="kernel.json", close_client=Mock()),
    ]
    widget = Mock(clients=clients)
    widget.get_related_clients.side_effect = lambda client, open_clients: [
        other
        for other in open_clients
        if other is not client and other.connection_file == client.connection_file
    ]
    wait_all = mocker.patch.object(KernelHandler, "wait_all_shutdown_threads")

    IPythonConsoleWidget.close_all_clients(widget)

    for client in clients:
        client.close_client.assert_called_once_with(
            True,
            close_console=True,
        )
    wait_all.assert_called_once_with()
    widget.close_cached_kernel.assert_called_once_with()
