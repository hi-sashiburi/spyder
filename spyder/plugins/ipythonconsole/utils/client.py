# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Kernel Client subclass."""

# Standard library imports
from concurrent.futures import Future, wait
import logging
import socket

# Third party imports
import asyncssh
from qtpy.QtCore import Signal
from qtconsole.client import QtKernelClient, QtZMQSocketChannel
from traitlets import Type

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.translations import _
from spyder.plugins.ipythonconsole import SpyderKernelError


logger = logging.getLogger(__name__)


class KernelClientTunneler:
    """Class to handle SSH tunneling for a kernel connection."""

    def __init__(self, ssh_connection, *, _close_conn_on_exit=False):
        self.ssh_connection = ssh_connection
        self._port_forwarded = {}
        self._close_conn_on_exit = _close_conn_on_exit

    def __del__(self):
        """Close all port forwarders and the connection if required."""
        for forwarder in self._port_forwarded.values():
            forwarder.close()

        if self._close_conn_on_exit:
            self.ssh_connection.close()

    @classmethod
    @AsyncDispatcher(loop="asyncssh", early_return=False)
    async def new_connection(cls, *args, **kwargs):
        """Create a new SSH connection."""
        return cls(
            await asyncssh.connect(*args, **kwargs, known_hosts=None),
            _close_conn_on_exit=True,
        )

    @classmethod
    def from_connection(cls, ssh_connection):
        """Create a new KernelTunnelHandler from an existing connection."""
        return cls(ssh_connection)

    @AsyncDispatcher(loop="asyncssh", early_return=False)
    async def forward_port(self, remote_host, remote_port):
        """Forward a port through the SSH connection."""
        local = self._get_free_port()
        try:
            self._port_forwarded[(remote_host, remote_port)] = (
                await self.ssh_connection.forward_local_port(
                    '127.0.0.1', local, remote_host, remote_port
                )
            )
        except asyncssh.Error as err:
            raise SpyderKernelError(
                _(
                    "It was not possible to open an SSH tunnel to connect to "
                    "the remote kernel. Please check your credentials and the "
                    "server connection status."
                )
            ) from err
        return local

    @staticmethod
    def _get_free_port():
        """Request a free port from the OS."""
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]


class SpyderKernelClient(QtKernelClient):
    # Enable receiving messages on control channel.
    # Useful for pdb completion
    control_channel_class = Type(QtZMQSocketChannel)
    sig_spyder_kernel_info = Signal(object)

    def stop_channels(self):
        """Stop channels after pending stream callbacks have finished.

        Channel streams run on the client's I/O loop. Before delegating their
        closure to jupyter-client, disable new receive callbacks on that loop
        and enqueue a barrier behind the callbacks that are already pending.
        This prevents a pending callback from accessing a stream or socket
        after jupyter-client closes it.

        Each of these pre-teardown waits has a five-second safety limit,
        matching jupyter-client's channel-close timeout. The first limit
        covers all channel streams concurrently, rather than five seconds per
        stream. The barrier has its own limit, so these waits can add up to ten
        seconds if the I/O loop is unresponsive. On a responsive loop, both
        finish almost immediately. Dependency-owned teardown has its own
        separate timeouts.
        """
        if self.ioloop_thread and self.ioloop_thread.is_alive():
            ioloop = self.ioloop
            futures = []
            channels = [
                self._shell_channel,
                self._iopub_channel,
                self._stdin_channel,
                self._control_channel,
            ]

            for channel in channels:
                if channel is None or channel.stream is None:
                    continue

                future = Future()
                stream = channel.stream

                def stop_receiving(stream=stream, future=future):
                    try:
                        stream.on_recv(None)
                    except Exception as error:
                        future.set_exception(error)
                    else:
                        future.set_result(None)

                ioloop.add_callback(stop_receiving)
                futures.append(future)

            # Run all stream callbacks concurrently. The timeout is a single
            # safety bound for the group, not an additional wait per stream.
            done, pending = wait(futures, timeout=5)
            for future in done:
                try:
                    future.result()
                except Exception as error:
                    logger.warning(
                        "Error stopping kernel channel stream callbacks: %s",
                        error,
                    )
            if pending:
                logger.warning(
                    "Timed out stopping kernel channel stream callbacks"
                )

            if futures:
                # This callback runs after events already queued on the I/O
                # loop, providing a barrier before dependency-owned teardown.
                drained = Future()
                ioloop.add_callback(drained.set_result, None)
                try:
                    drained.result(timeout=5)
                except Exception as error:
                    logger.warning(
                        "Error draining kernel channel events: %s", error
                    )

        super().stop_channels()

    def _handle_kernel_info_reply(self, rep):
        """Check spyder-kernels version."""
        super()._handle_kernel_info_reply(rep)
        spyder_kernels_info = rep["content"].get("spyder_kernels_info", None)
        self.sig_spyder_kernel_info.emit(spyder_kernels_info)

    def tunnel_to_kernel(
        self, hostname=None, sshkey=None, password=None, ssh_connection=None
    ):
        """Tunnel to remote kernel."""
        if ssh_connection is not None:
            self.__tunnel_handler = KernelClientTunneler.from_connection(
                ssh_connection
            )
        elif sshkey is not None:
            self.__tunnel_handler = KernelClientTunneler.new_connection(
                password=password,
                client_keys=[sshkey],
                **self._split_shh_address(hostname),
            )
        else:
            self.__tunnel_handler = KernelClientTunneler.new_connection(
                password=password,
                **self._split_shh_address(hostname),
            )

        (
            self.shell_port,
            self.iopub_port,
            self.stdin_port,
            self.hb_port,
            self.control_port,
        ) = (
            self.__tunnel_handler.forward_port(self.ip, port)
            for port in (
                self.shell_port,
                self.iopub_port,
                self.stdin_port,
                self.hb_port,
                self.control_port,
            )
        )
        self.ip = "127.0.0.1"  # Tunneled to localhost

    @staticmethod
    def _split_shh_address(address):
        """Split ssh address into host and port."""
        user_host, _, port = address.partition(':')
        user, _, host = user_host.rpartition('@')
        return {
            'username': user if user else None,
            'host': host if host else None,
            'port': int(port) if port else None
        }
