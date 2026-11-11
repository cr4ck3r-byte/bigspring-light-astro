#!/bin/bash
# One-time administrator step (run with sudo on the VPS): move the landing to a
# release tree like the client/admin apps, so Actions can deploy as `omar`.
# If the landing stops responding, the previous directory is restored.
set -eu
R=/var/www/barbersoftly-releases/landing
W=/var/www/wwwbarbersoftly
TS=$(date +%Y%m%d-%H%M%S)
test ! -e "$R"
test -d "$W" && test ! -L "$W"
mkdir -p "$R/releases" "$R/uploads"
cp -a "$W" "$R/releases/bootstrap-$TS"
ln -s "$R/releases/bootstrap-$TS" "$R/current"
ln -s "$R/releases/bootstrap-$TS" "$R/previous"
printf '{"application": "landing", "webRoot": "%s"}' "$W" > "$R/.deployment-target.json"
touch "$R/deploy.lock"
chown -R omar:omar "$R"
mv "$W" "$W.pre-cd-$TS"
ln -s "$R/current" "$W"
if curl -fsS --max-time 10 --resolve barbersoftly.com:443:127.0.0.1 https://barbersoftly.com/ | grep -q "barbersoftly"; then
  echo "OK: $W -> $R/current (bootstrap-$TS). Previous directory: $W.pre-cd-$TS"
else
  rm "$W" && mv "$W.pre-cd-$TS" "$W"
  echo "ERROR: the landing did not respond; $W was restored"
  exit 1
fi
