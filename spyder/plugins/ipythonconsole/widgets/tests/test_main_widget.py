from unittest.mock import Mock

from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget,
)


def test_pending_client_setup_is_ignored_during_mainwindow_close():
    """A late environment result cannot start kernels during shutdown."""
    widget = Mock(mainwindow_close=True)
    client = Mock()
    future = Mock()
    future.result.return_value = {}

    IPythonConsoleWidget._connect_new_client_to_kernel(
        widget,
        cache=True,
        path_to_custom_interpreter=None,
        client=client,
        future=future,
    )

    widget.get_cached_kernel.assert_not_called()
    client.connect_kernel.assert_not_called()
