# Changes

## Unreleased

- Prevent ZMQ callback errors when a project is closed during startup by
  closing IPython console channel streams before their sockets are torn down
  ([spyder-ide/spyder#25623](https://github.com/spyder-ide/spyder/issues/25623)).
