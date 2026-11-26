# Windows-native sshd on the laptop: blocked on one elevated command (2026-11-26)

Goal: let gx10 reach a real **Windows** shell on the laptop (`ELTON2026`, 192.168.2.51), not
just the WSL shell that currently answers on port 22.

## What is actually there now

| Fact | Evidence |
|------|----------|
| Port 22 on `192.168.2.51` is the **Ubuntu sshd inside WSL** | banner `SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.20`, host `Elton2026`, mirrored `eth1 192.168.2.51/24` |
| No Windows `sshd.exe` exists on the laptop | `ops-windows-sshd.yml` run `45786756563`: `C:\Windows\System32\OpenSSH\sshd.exe : False`, `C:\Program Files\OpenSSH\sshd.exe : False` |
| The runner cannot install it | same run: `elevated : False`; earlier run: `Get-WindowsCapability` → "The requested operation requires elevation." |
| A userland `sshd` is therefore impossible too | the userland mode found no binary and reported `USERLAND_SSHD: BLOCKED - no sshd.exe on this machine.` |
| gx10 cannot reach a Windows shell | `192.168.2.51:2222` closed → `Connection refused` |

## The one command that unblocks it

Run **once**, in an **elevated** PowerShell (Administrator) on the laptop — not by me, the
runner is a non-elevated user process:

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Set-Service sshd -StartupType Automatic
Start-Service sshd
```

Then, to give gx10 access, dispatch `Ops - Windows OpenSSH Server` with `mode=enable`
(installs/enables + opens the firewall for `192.168.2.0/24`), and authorize gx10's key:

```powershell
# elevated, on the laptop (administrators log in through this file, not the user profile one)
Add-Content C:\ProgramData\ssh\administrators_authorized_keys `
  "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIItq2fgOOdjzzLf1ywjJsVbavp3iGOsxJocvnR/deAKX eaguiar2015@gx10->ELTON2026"
icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
```

Port conflict to decide first: Windows `sshd` wants 22, which the WSL sshd already holds (and
which `ssh laptop` from gx10 currently uses). Either give the Windows service another port
(`Port 2223` in `C:\ProgramData\ssh\sshd_config` + firewall rule) or move the WSL sshd off 22.

## What was added so this does not stay a mystery

`Ops - Windows OpenSSH Server` (`.github/workflows/ops-windows-sshd.yml`, PR #1228) gained
`mode=userland`: it finds whatever `sshd.exe` is on disk, generates its own host key, writes a
user-scoped config (`port`, `AuthorizedKeysFile`, `PasswordAuthentication no`, `StrictModes no`),
authorizes gx10's public key and starts it — all without elevation. With no binary present it
prints the command above and exits clean instead of failing, because that install genuinely
cannot be performed from a non-elevated runner. The same PR fixed the `mode`/`subnet` inputs,
which had printed the literal `$('{{ inputs.mode }}')`.

## Status

Reverse shell access **works into WSL** (`ssh laptop` → gx10 `~/.ssh/id_ed25519_laptop`; `root`
via `~/.ssh/id_ed25519`). A Windows shell stays blocked until someone runs the three-line
elevated command on the laptop.
