#!/usr/bin/env bash
# setup_break_glass.sh — Layer 3: a route into this machine that does NOT depend on
# Anthropic's Remote Control. Tailscale (in WSL, with Tailscale SSH) + tmux.
#
# Run ONCE, by the owner, in a WSL terminal — it needs sudo, and `tailscale up`
# prints a login URL that only the owner's Tailscale account can complete.
#
#   bash /mnt/d/owner/dev/MandrakeWorkflows/skills/claude-remote-control/scripts/setup_break_glass.sh
#
# WHY TAILSCALE SSH AND NOT sshd: Tailscale SSH authenticates by tailnet identity,
# so there is no sshd config, no authorized_keys, no exposed port on the LAN — the
# machine is reachable only from devices logged into the same tailnet (the phone).
#
# WHY IN WSL AND NOT ON THE WINDOWS HOST: Tailscale SSH is Linux-only, WSL already
# runs systemd here (so tailscaled survives as a service), and everything the
# break-glass path needs — git, claude, tmux — lives in WSL. The cost is that WSL
# must be running for the machine to be reachable; `wsl_keepalive.vbs` (registered
# as a logon task by this script's Windows half) covers that after a reboot.
#
# After this completes, from the phone (Tailscale app + Termius/Blink):
#     ssh owner@desktop-wsl
#     tmux new -s rc  (or tmux attach -t rc)
#     cd /home/owner/rm/bench && claude --remote-control 'RESCUE' --resume
set -euo pipefail

echo "== 1/4 tailscale"
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
sudo systemctl enable --now tailscaled
sleep 2

echo "== 2/4 tailscale up (Tailscale SSH on). If a URL prints, open it and log in — that step is yours."
sudo tailscale up --ssh --hostname desktop-wsl --accept-dns=false

echo "== 3/4 tmux"
command -v tmux >/dev/null || sudo apt-get install -y tmux

echo "== 4/4 result"
tailscale ip -4
tailscale status | head -5
echo
echo "Reach it from the phone as:  ssh owner@desktop-wsl   (or the 100.x address above)"
echo "Then record the result in /mnt/d/owner/dev/MandrakeWorkflows/skills/claude-remote-control/references/incident-log.md (your own, private)"
