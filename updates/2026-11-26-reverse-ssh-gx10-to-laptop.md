# Reverse SSH: gx10 -> laptop (2026-11-26)

Status: **working both ways**. `gx10` can now log into the laptop, completing the pair that
started with `laptop -> gx10` (see `2026-11-26-laptop-ssh-key-delivery.md` behaviour in
`.github/workflows/ops-install-laptop-key.yml`).

## What was broken

`laptop -> gx10` worked (`ssh gx10` from `C:\Users\zerou\.ssh\config`), but the return path
failed. `gx10 -> laptop` had no key authorized on the laptop, and the laptop had no Windows
`sshd` at all: the diagnostic run of `.github/workflows/ops-windows-sshd.yml` reported
`ELTON2026\zerou`, `elevated: False`, no `sshd` service, and port 22 closed, with the
capability query failing on "The requested operation requires elevation".

## The misleading part (why two attempts failed)

Later the laptop answered on `192.168.2.51:22`, but with a **Linux** banner:

```
192.168.2.51 | SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.20
192.168.2.52 | SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.20   (gx10)
192.168.2.32 | SSH-2.0-OpenSSH_for_Windows_9.5             (desktop-081g9oh)
```

So the listener is the **Ubuntu sshd inside the laptop's WSL distro**, reached through a
Windows loopback forward, not the Windows OpenSSH service. Consequences:

- Run `45782875281` wrote the key to `C:\Users\zerou\.ssh\authorized_keys` — the right file
  for Windows sshd, the wrong file for WSL sshd — and its `ssh zerou@127.0.0.1` self-test
  returned `Permission denied (publickey)`.
- Run `45784767282` (a `wsl.exe`-driven job from the Windows runner) did land the key in the
  WSL user's `~/.ssh/authorized_keys` — `key already present in /home/zerou/.ssh/authorized_keys`
  — yet its self-test could never pass: the laptop only ever holds the *public* half, and handing
  a public key to `ssh -i` cannot authenticate. The job now verifies what it actually can (key
  line present, `700`/`600` permissions, effective `sshd -T` settings) and leaves the real login
  check to gx10, which is the only holder of the private key.

The laptop auth log made this unambiguous:

```
Elton2026 sshd[52954]: Accepted publickey for root from 192.168.2.52 port 35838 ssh2:
  ED25519 SHA256:k5Pr5djY4USixRr6edc157CKZ8/J8D7eR4yXlxZd6Xo
Elton2026 sshd[53381]: Invalid user eaguiar2015 from 192.168.2.52      <- no such WSL user
Elton2026 sshd[54231]: Connection closed by authenticating user zerou 127.0.0.1 [preauth]
```

## What changed

| Change | Where |
|--------|-------|
| Manual workflow that writes gx10's ed25519 public key into the laptop's WSL `authorized_keys` (driven through `wsl.exe` from the Windows runner, because the WSL runner slots were busy), fixes `700`/`600` for `StrictModes`, prints fingerprints and the effective `sshd -T` settings, and asserts the key line is present | `.github/workflows/ops-install-gx10-pubkey.yml` (PRs #1216, #1218, #1220, #1222) |
| `mode` / `subnet` inputs of the Windows-sshd workflow repaired — they printed the literal `$('{{ inputs.mode }}')` because the template was nested in single quotes | `.github/workflows/ops-windows-sshd.yml` (PR #1216) |
| Header note that `ops-install-laptop-key.yml` is one-shot and its secret is gone | `.github/workflows/ops-install-laptop-key.yml` (PR #1216) |
| Repo secret `GX10_LAPTOP_KEY_B64` (private key, base64) **deleted** now that the delivery is verified | repo settings |
| Duplicate `zerou@DESKTOP-081G9OH` line removed from gx10's `~/.ssh/authorized_keys` (byte-identical copy); backup `authorized_keys.bak-2026-11-26b` | `gx10:~/.ssh` |
| `Host laptop` alias (192.168.2.51, user `zerou`, `~/.ssh/id_ed25519_laptop`, `IdentitiesOnly yes`); backup `config.bak-2026-11-26` | `gx10:~/.ssh/config` |

The Windows job in the reverse-key workflow is `continue-on-error` and only records state —
writing the Windows profile file cannot help a WSL sshd.

## Verification (run on gx10, 2026-11-26)

```
$ ssh laptop 'echo LAPTOP_ALIAS_OK; hostname; id -un'
LAPTOP_ALIAS_OK
Elton2026
zerou

$ ssh -i ~/.ssh/id_ed25519 root@192.168.2.51 'echo OK; hostname; id -un'
OK
Elton2026
root
```

Key split, so each direction uses its own credential:

- `laptop -> gx10`: `C:\Users\zerou\.ssh\gx10_laptop`, fingerprint
  `SHA256:XQ/T5xaJX1889a2YNWDIce//nxq3iDVCI8m4DcgOyBA` (`zerou@ELTON2026->gx10`).
- `gx10 -> laptop` as `zerou`: `~/.ssh/id_ed25519_laptop`, fingerprint
  `SHA256:ZjNU/ZHXVCG1rXnENGTYWdyGQ2lGHgt6crN9kgmR0kc` (`eaguiar2015@gx10->ELTON2026`).
- `gx10 -> laptop` as `root`: `~/.ssh/id_ed25519`, fingerprint
  `SHA256:k5Pr5djY4USixRr6edc157CKZ8/J8D7eR4yXlxZd6Xo` (already present in root's
  `authorized_keys`; no passphrase, so treat it as a LAN-only credential).

## Known limits

- The laptop still has **no Windows-native sshd**. Anything that must run as a Windows
  account over SSH needs one elevated command on the laptop:
  `Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0; Start-Service sshd`.
- The WSL sshd is reachable only while WSL is running and its port forward is up.
- LAN-only: both hosts are on `192.168.2.0/24`; none of these keys should be reused off-LAN.
