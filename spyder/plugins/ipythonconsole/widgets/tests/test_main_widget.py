from unittest.mock import Mock, patch

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


def test_environment_result_for_closed_client_does_not_start_kernel():
    """Project restart cannot attach a late kernel to a removed console."""
    widget = Mock(mainwindow_close=False, clients=[])
    client = Mock()
    future = Mock()
    future.result.return_value = {}

    IPythonConsoleWidget._connect_new_client_to_kernel(
        widget, False, None, client, future
    )

    widget.get_cached_kernel.assert_not_called()
    client.connect_kernel.assert_not_called()
    client.show_kernel_error.assert_not_called()


def test_environment_result_still_connects_current_client():
    """A current console receives its requested kernel after env discovery."""
    client = Mock()
    widget = Mock(mainwindow_close=False, clients=[client])
    future = Mock()
    future.result.return_value = {"TEST_ENV": "value"}

    with patch(
        "spyder.plugins.ipythonconsole.widgets.main_widget.SpyderKernelSpec"
    ) as kernel_spec:
        IPythonConsoleWidget._connect_new_client_to_kernel(
            widget, False, None, client, future
        )

    assert kernel_spec.return_value.env == {"TEST_ENV": "value"}
    widget.get_cached_kernel.assert_called_once_with(
        kernel_spec.return_value, cache=False
    )
    client.connect_kernel.assert_called_once_with(
        widget.get_cached_kernel.return_value
    )
