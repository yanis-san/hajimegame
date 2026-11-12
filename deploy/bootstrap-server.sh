#!/usr/bin/env bash
# One-time preparation of a fresh Ubuntu or Debian server for the production stack. Run it as root:
#
#   sudo bash bootstrap-server.sh "<ssh public key the pipeline will use>" hajime.yourdomain.com you@yourmail.com ghcr.io/<user>/<repo>
#
# It installs Docker from Docker's own repository, creates a `deploy` user (the pipeline logs in as it),
# opens only ports 22, 80 and 443 in the firewall, turns on automatic security updates and fail2ban, and writes
# /opt/hajime/.env with a generated metrics token. It can be run again safely.
#
# SSH hardening (no password logins) is opt-in, because turning it on before a key works would lock you out:
#   HARDEN_SSH=1 sudo -E bash bootstrap-server.sh ...    (only after `ssh deploy@server` works with your key)
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "run this as root (sudo)" >&2; exit 1; }
PUBKEY="${1:?usage: bootstrap-server.sh <ssh-public-key> <domain> <acme-email> <image-prefix>}"
DOMAIN="${2:?missing domain}"
ACME_EMAIL="${3:?missing email}"
IMAGE_PREFIX="${4:?missing image prefix, e.g. ghcr.io/user/repo}"
[[ "$PUBKEY" == ssh-* ]] || { echo "the first argument must be an SSH public key (ssh-ed25519 AAAA...)" >&2; exit 1; }

export DEBIAN_FRONTEND=noninteractive
# shellcheck disable=SC1091
. /etc/os-release
[[ "$ID" == "ubuntu" || "$ID" == "debian" ]] || { echo "only Ubuntu and Debian are supported (found $ID)" >&2; exit 1; }

echo "==> packages"
apt-get update -y
apt-get install -y ca-certificates curl gnupg ufw fail2ban unattended-upgrades

echo "==> docker"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
    >/etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi
systemctl enable --now docker

echo "==> deploy user"
id deploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash deploy
usermod -aG docker deploy   # note: the docker group is root-equivalent; this user only runs the pipeline
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
touch /home/deploy/.ssh/authorized_keys
grep -qxF "$PUBKEY" /home/deploy/.ssh/authorized_keys || echo "$PUBKEY" >>/home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys

echo "==> /opt/hajime"
install -d -m 750 -o deploy -g deploy /opt/hajime
if [[ ! -f /opt/hajime/.env ]]; then
  umask 077
  cat >/opt/hajime/.env <<EOF
DOMAIN=$DOMAIN
ACME_EMAIL=$ACME_EMAIL
IMAGE_PREFIX=$IMAGE_PREFIX
HAJIME_METRICS_TOKEN=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
POSTGRES_PASSWORD=$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')
HAJIME_SENTRY_DSN=
DRAIN_SECONDS=180
EOF
  chown deploy:deploy /opt/hajime/.env
  chmod 600 /opt/hajime/.env
  echo "    wrote /opt/hajime/.env"
else
  # an .env from before the database existed gets its password, nothing else is changed
  if ! grep -q '^POSTGRES_PASSWORD=' /opt/hajime/.env; then
    (umask 077; printf 'POSTGRES_PASSWORD=%s\n' "$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')" >>/opt/hajime/.env)
    echo "    added POSTGRES_PASSWORD to the existing /opt/hajime/.env"
  else
    echo "    /opt/hajime/.env already exists: left untouched"
  fi
fi

echo "==> firewall (ssh, http, https)"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable
# Docker publishes ports around ufw: that is why the app containers publish none, only Caddy does.

echo "==> automatic security updates and fail2ban"
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
systemctl enable --now fail2ban

if [[ "${HARDEN_SSH:-0}" == "1" ]]; then
  echo "==> ssh hardening"
  cat >/etc/ssh/sshd_config.d/99-hajime.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
EOF
  sshd -t   # a broken config stops the script here, before anything is reloaded
  systemctl reload ssh 2>/dev/null || systemctl reload sshd
  echo "    password logins are now disabled"
else
  echo "==> ssh hardening skipped (HARDEN_SSH=1 to enable it once your key works)"
fi

HOST_KEY="$(ssh-keyscan -t ed25519 localhost 2>/dev/null | sed 's/^localhost/<server-address>/')"
cat <<EOF

Done. Next steps:
  1. DNS: point $DOMAIN (A and AAAA) to this server.
  2. GitHub repository, Settings > Secrets and variables > Actions:
       secrets   DEPLOY_HOST (this server's address), DEPLOY_USER (deploy), DEPLOY_SSH_KEY (the PRIVATE key
                 matching the public key you passed), DEPLOY_KNOWN_HOSTS (the line below)
       variables DEPLOY_ENABLED=true, DEPLOY_DOMAIN=$DOMAIN
  3. Push to main: the pipeline tests, builds, scans, publishes and deploys.

DEPLOY_KNOWN_HOSTS:
$HOST_KEY
EOF
