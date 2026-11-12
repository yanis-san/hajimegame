#!/usr/bin/env bash
# Sets up a new server AND the GitHub repository in one command, from your own computer (Git Bash on Windows).
#
#   ./deploy/provision.sh root@203.0.113.10 hajime.yourdomain.com you@yourmail.com
#
# What it does, in order:
#   1. creates an SSH key for the pipeline (~/.ssh/hajime-deploy) if you do not have one yet;
#   2. shows the server's SSH fingerprint and waits for you to confirm it is the one your provider shows;
#   3. runs deploy/bootstrap-server.sh on the server (Docker, deploy user, firewall, updates, .env);
#   4. checks that the pipeline's key can log in;
#   5. stores the secrets and variables in the GitHub repository and creates the "production" environment.
# After that, a push to main deploys. It can be run again safely; the server's /opt/hajime/.env is kept as it is
# (edit that file by hand to change the domain later).
#
# Needs: ssh, scp, ssh-keygen, the GitHub CLI logged in (gh auth login), and root access to the new server (the
# password or key your provider gave you), plus a domain whose DNS you can edit.
#
# Options:  --dry-run       print what would happen, change nothing (no network)
#           --yes           do not ask to confirm the server fingerprint (only if you checked it another way)
#           --harden-ssh    also turn off SSH password logins on the server. Only if you can log in with a KEY
#                           as root or deploy and do not need the root password afterwards.
set -euo pipefail

DRY=0 YES=0 HARDEN=0
args=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --yes) YES=1 ;;
    --harden-ssh) HARDEN=1 ;;
    -h | --help) sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) args+=("$arg") ;;
  esac
done
[[ ${#args[@]} -eq 3 ]] || { echo "usage: provision.sh [--dry-run] [--yes] [--harden-ssh] user@server domain email" >&2; exit 2; }
SERVER="${args[0]}" DOMAIN="${args[1]}" EMAIL="${args[2]}"
[[ "$SERVER" == *@* ]] || { echo "the server must look like root@203.0.113.10" >&2; exit 2; }
[[ "$DOMAIN" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}$ ]] || { echo "invalid domain: $DOMAIN" >&2; exit 2; }
[[ "$EMAIL" == *@*.* ]] || { echo "invalid email: $EMAIL" >&2; exit 2; }
LOGIN="${SERVER%@*}"
HOST="${SERVER#*@}"
HERE="$(cd "$(dirname "$0")" && pwd)"
KEY="$HOME/.ssh/hajime-deploy"

say() { printf '\n==> %s\n' "$*"; }
run() { if ((DRY)); then printf '    [dry-run] %s\n' "$*"; else "$@"; fi; }

for tool in ssh scp ssh-keygen gh; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool" >&2; exit 1; }
done
((DRY)) || gh auth status >/dev/null 2>&1 || { echo "log in to GitHub first: gh auth login" >&2; exit 1; }
if ((DRY)); then REPO="owner/repository"; else REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"; fi
IMAGE_PREFIX="ghcr.io/$(printf '%s' "$REPO" | tr '[:upper:]' '[:lower:]')"
echo "server:     $SERVER"
echo "domain:     $DOMAIN"
echo "repository: $REPO  (images: $IMAGE_PREFIX)"

say "1/5 SSH key for the pipeline"
if [[ -f "$KEY" ]]; then
  echo "    $KEY already exists, reusing it"
else
  run ssh-keygen -t ed25519 -N "" -C hajime-pipeline -f "$KEY"
fi

say "2/5 Server fingerprint"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
KNOWN="$TMP/known_hosts"
if ((DRY)); then
  echo "    [dry-run] ssh-keyscan -t ed25519 $HOST, then compare the fingerprint with your provider's console"
  printf '%s ssh-ed25519 AAAA-dry-run\n' "$HOST" >"$KNOWN"
else
  ssh-keyscan -t ed25519 "$HOST" 2>/dev/null >"$KNOWN" || true
  [[ -s "$KNOWN" ]] || { echo "cannot reach $HOST on port 22 (is the server up and the address right?)" >&2; exit 1; }
  ssh-keygen -lf "$KNOWN"
  if ((!YES)); then
    echo "    Compare this fingerprint with the one in your provider's console or e-mail."
    read -r -p "    Is it the same? [y/N] " answer
    [[ "$answer" == y || "$answer" == Y ]] || { echo "stopped: nothing was changed" >&2; exit 1; }
  fi
fi
SSH_OPTS=(-o "UserKnownHostsFile=$KNOWN" -o StrictHostKeyChecking=yes -o BatchMode=no)

say "3/5 Preparing the server (Docker, deploy user, firewall, automatic updates)"
SUDO=""
[[ "$LOGIN" == root ]] || SUDO="sudo "
PUBKEY="$(cat "$KEY.pub" 2>/dev/null || echo 'ssh-ed25519 AAAA-dry-run hajime-pipeline')"
run scp "${SSH_OPTS[@]}" "$HERE/bootstrap-server.sh" "$SERVER:/tmp/hajime-bootstrap.sh"
BOOTSTRAP="bash /tmp/hajime-bootstrap.sh '$PUBKEY' '$DOMAIN' '$EMAIL' '$IMAGE_PREFIX'"
run ssh "${SSH_OPTS[@]}" "$SERVER" "${SUDO}$BOOTSTRAP"

say "4/5 Checking that the pipeline can log in"
run ssh "${SSH_OPTS[@]}" -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes "deploy@$HOST" "docker version --format 'docker {{.Server.Version}} ready'"

if ((HARDEN)); then
  say "    Turning off SSH password logins (the pipeline's key just worked)"
  run ssh "${SSH_OPTS[@]}" "$SERVER" "${SUDO}env HARDEN_SSH=1 $BOOTSTRAP"
fi
run ssh "${SSH_OPTS[@]}" "$SERVER" "rm -f /tmp/hajime-bootstrap.sh"

say "5/5 GitHub: secrets, variables and the production environment"
KNOWN_LINE="$(grep -v '^#' "$KNOWN" | head -n1)"
run gh secret set DEPLOY_HOST --repo "$REPO" --body "$HOST"
run gh secret set DEPLOY_USER --repo "$REPO" --body deploy
if ((DRY)); then
  run gh secret set DEPLOY_SSH_KEY --repo "$REPO" "< $KEY"
else
  gh secret set DEPLOY_SSH_KEY --repo "$REPO" <"$KEY"
fi
run gh secret set DEPLOY_KNOWN_HOSTS --repo "$REPO" --body "$KNOWN_LINE"
run gh variable set DEPLOY_DOMAIN --repo "$REPO" --body "$DOMAIN"
run gh variable set DEPLOY_ENABLED --repo "$REPO" --body true
run gh api --method PUT "repos/$REPO/environments/production" --silent

cat <<EOF

Done. Two things are left, both yours:

  1. DNS: create an A record  $DOMAIN  ->  $HOST   (and AAAA if the server has an IPv6 address).
     The first deployment obtains the HTTPS certificate, which only works once the record exists.
  2. Push to main:  git push origin main
     Watch it in the repository's Actions tab. The site is live at https://$DOMAIN when the "Deploy to
     production" job turns green; its last step tests the live site from outside.

Good to do once it works:
  - Settings > Environments > production > Required reviewers: one click to approve each deployment.
  - Settings > Branches: require the CI checks before merging to main.
  - Keep ~/.ssh/hajime-deploy private: it is the pipeline's only way into the server.
EOF
