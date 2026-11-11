#!/usr/bin/env bash
# Upload the tested landing build and activate it, or roll back. Runs in Actions.
set -euo pipefail

operation="${1:?Expected deploy or rollback}"
[[ "$operation" == deploy || "$operation" == rollback ]]
[[ "${DEPLOY_SSH_HOST:?Missing DEPLOY_SSH_HOST}" =~ ^[a-zA-Z0-9.-]+$ ]]
[[ "${DEPLOY_SSH_USER:?Missing DEPLOY_SSH_USER}" =~ ^[a-z_][a-z0-9_-]*$ ]]
port="${DEPLOY_SSH_PORT:-22}"
[[ "$port" =~ ^[0-9]{1,5}$ ]] && ((10#$port > 0 && 10#$port < 65536))

key_directory="$(mktemp -d "${RUNNER_TEMP:?}/landing-ssh.XXXXXXXX")"
trap 'rm -f -- "$key_directory/key" "$key_directory/known_hosts"; rmdir -- "$key_directory"' EXIT
printf '%s\n' "${DEPLOY_SSH_KEY:?Missing DEPLOY_SSH_KEY}" > "$key_directory/key"
printf '%s\n' "${DEPLOY_KNOWN_HOSTS:?Missing DEPLOY_KNOWN_HOSTS}" > "$key_directory/known_hosts"
chmod 700 "$key_directory"
chmod 600 "$key_directory/key" "$key_directory/known_hosts"
options=(-i "$key_directory/key" -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$key_directory/known_hosts" -o ConnectTimeout=15)
host="$DEPLOY_SSH_USER@$DEPLOY_SSH_HOST"
root="/var/www/barbersoftly-releases/landing"

if [[ "$operation" == rollback ]]; then
  ssh "${options[@]}" -p "$port" "$host" "python3 - rollback" < scripts/deploy_landing.py
  exit
fi

[[ "${GITHUB_SHA:?}" =~ ^[a-f0-9]{40}$ ]]
[[ "${GITHUB_RUN_ID:?}" =~ ^[0-9]+$ ]]
[[ "${GITHUB_RUN_ATTEMPT:?}" =~ ^[0-9]+$ ]]
release_id="$GITHUB_SHA-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
archive="release/site.tar.gz"
checksum="$(sha256sum "$archive" | cut -d ' ' -f 1)"
# The release tree is bootstrapped by an administrator; never create it here.
ssh "${options[@]}" -p "$port" "$host" "test -f '$root/.deployment-target.json' && test -w '$root/uploads'"
scp "${options[@]}" -P "$port" "$archive" "$host:$root/uploads/$release_id.tar.gz.part"
ssh "${options[@]}" -p "$port" "$host" "mv -- '$root/uploads/$release_id.tar.gz.part' '$root/uploads/$release_id.tar.gz'"
ssh "${options[@]}" -p "$port" "$host" "python3 - deploy --release $release_id --sha256 $checksum" < scripts/deploy_landing.py
