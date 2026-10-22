# Banking investigation checkpoint

This branch contains the redesigned application and its reproducible local banking investigation. It preserves the preceding project history on the main branch.

See [the current demo guide](docs/BANKING_DEMO_GUIDE.md) for the measured findings, recovery checks and remaining research limitations. The demo uses retained AWS measurements; it starts no cloud resources. AWS research compute has been terminated.

## Clone and start

Clone with `git clone --recurse-submodules` to obtain the pinned public Bank of Anthos source dependency. For an existing clone, run `git submodule update --init`.

Use Python 3.12 and the existing requirements files to prepare a virtual environment. Build the frontend with `npm --prefix frontend ci` and `npm --prefix frontend run build`. Start `START_REDESIGN.ps1 -Port 8012` and open http://127.0.0.1:8012/.

The local replay is reproducible with `python scripts/replay_banking_investigation.py`. It checks retained file hashes and recomputes the request-to-ledger matches. Credentials, private keys, local databases, package caches, installers and temporary test outputs are excluded from Git. The full SQL backup remains local on D:.

## Verification and scope

The current checkpoint passed 188 Python tests and four browser acceptance tests. The banking replay provides measured-signature findings and a separately identified investigator-assisted integrity probe. It does not establish independently validated banking GNN accuracy or a novelty advantage. The recorded recovery is temporary; the permanent application fix remains pending.
