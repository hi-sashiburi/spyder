from unittest.mock import Mock

from qtpy.compat import isalive
from qtpy.QtCore import QCoreApplication, QEvent, QObject, Signal

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


def test_kernel_ready_stops_when_banner_deletes_shell():
    """Banner setup cannot leave a deleted shell emitting ready."""

    class FakeShell(QObject):
        sig_kernel_is_ready = Signal()

    shell = FakeShell()
    shell.shutting_down = False
    shell._control = ControlWidget()
    shell.kernel_handler = Mock(
        connection_state=KernelConnectionState.SpyderKernelReady,
    )
    shell.setup_spyder_kernel = Mock()
    ready = Mock()
    shell.sig_kernel_is_ready.connect(ready)

    def delete_shell():
        shell.deleteLater()
        QCoreApplication.sendPostedEvents(shell, QEvent.DeferredDelete)

    shell._show_banner = delete_shell

    ShellWidget.handle_kernel_is_ready(shell)

    ready.assert_not_called()


def test_banner_stops_when_generation_deletes_control():
    """Banner generation cannot leave a deleted console being accessed."""
    control = ControlWidget()

    def delete_control():
        control.deleteLater()
        QCoreApplication.sendPostedEvents(control, QEvent.DeferredDelete)
        return "banner"

    shell = Mock(
        is_external_kernel=False,
        _is_banner_shown=False,
        additional_options={"show_banner": False},
        _control=control,
    )
    shell.short_banner.side_effect = delete_control

    ShellWidget._show_banner(shell)

    shell._insert_plain_text.assert_not_called()
