from unittest.mock import Mock

from qtpy.compat import isalive
from qtpy.QtCore import QCoreApplication, QEvent

from spyder.plugins.ipythonconsole.utils.kernel_handler import (
    KernelConnectionState,
)
from spyder.plugins.ipythonconsole.widgets import ControlWidget
from spyder.plugins.ipythonconsole.widgets.shell import ShellWidget
from spyder.utils.qthelpers import qapplication

APP = qapplication()


def test_kernel_ready_is_ignored_after_control_is_deleted():
    """A queued kernel-ready callback cannot access a deleted console."""
    control = ControlWidget()
    control.deleteLater()
    QCoreApplication.sendPostedEvents(control, QEvent.DeferredDelete)
    assert not isalive(control)

    shell = Mock(
        shutting_down=False,
        _control=control,
        kernel_handler=Mock(
            connection_state=KernelConnectionState.SpyderKernelReady,
        ),
    )
    shell._show_banner.side_effect = control.textCursor

    ShellWidget.handle_kernel_is_ready(shell)

    shell.setup_spyder_kernel.assert_not_called()
    shell._show_banner.assert_not_called()
    shell.sig_kernel_is_ready.emit.assert_not_called()


def test_kernel_ready_stops_when_setup_deletes_control():
    """Kernel setup cannot leave a late callback using a deleted console."""
    control = ControlWidget()

    def delete_control():
        control.deleteLater()
        QCoreApplication.sendPostedEvents(control, QEvent.DeferredDelete)

    shell = Mock(
        shutting_down=False,
        _control=control,
        kernel_handler=Mock(
            connection_state=KernelConnectionState.SpyderKernelReady,
        ),
    )
    shell.setup_spyder_kernel.side_effect = delete_control
    shell._show_banner.side_effect = control.textCursor

    ShellWidget.handle_kernel_is_ready(shell)

    shell.setup_spyder_kernel.assert_called_once_with()
    shell._show_banner.assert_not_called()
    shell.sig_kernel_is_ready.emit.assert_not_called()
