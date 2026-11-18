# Changes

## Unreleased

- Prevent a delayed environment lookup from starting a kernel for a console
  already removed by a project restart. Ignore the callback before allocating
  a kernel or accessing the closed client, while preserving setup for active
  clients. This extends the existing application-exit guard to project closure.
