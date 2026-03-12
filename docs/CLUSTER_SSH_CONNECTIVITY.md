# Cluster SSH Connectivity

This note records the verified SSH pathway from `atlas` to `hades` and the minimal checks used to confirm that the control-plane host is reachable and ready for TK-AI operations.

## Verified Path

- Source node: `atlas`
- Destination node: `hades`
- Hades IP: `192.168.1.12`
- Result: passwordless SSH from `atlas` to `hades` is working

## Validation Sequence

From `atlas`, the following sequence was used:

1. Confirm local hostname and non-loopback addresses.
2. Confirm `hades` is reachable with `ping -c 3 192.168.1.12`.
3. Confirm SSH is listening on `192.168.1.12:22`.
4. Ensure an SSH key exists on `atlas`.
5. Confirm the public key is installed on `hades`.
6. Test a real SSH command:

```bash
ssh -o ConnectTimeout=5 zebadiee@192.168.1.12 "hostname && uptime && echo '✓ SSH connection successful'"
```

7. Verify the TK-AI workspace on `hades`:

```bash
ssh zebadiee@192.168.1.12 "cd ~/TK-Ai-Maxx && ls -la cluster/ tools/ | head -20"
```

8. Verify cluster health from `hades`:

```bash
ssh zebadiee@192.168.1.12 "cd ~/TK-Ai-Maxx && python3 tools/cluster_doctor.py"
```

## Expected Outcome

The final SSH test should return:

- the remote hostname
- uptime output
- `✓ SSH connection successful`

The `cluster_doctor.py` run on `hades` should confirm:

- `ATLAS TCP 11434: OK`
- `Ollama API: OK`
- `Signals file: OK`
- `Evidence file: OK`
- `Investigation daemon: active`

## Operational Use

This path is sufficient for:

- remote cartography from `atlas` back into the HADES control plane
- verifying the TK-AI deployment on `hades`
- invoking read-only diagnostics and cluster checks on demand

## Notes

- `ssh-copy-id` reported that keys were already installed, so the trust path was already present.
- This document only captures the verified `atlas -> hades` path. Hermes connectivity should be documented separately once verified the same way.
