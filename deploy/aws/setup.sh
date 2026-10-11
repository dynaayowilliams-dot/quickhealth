#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/dynaayowilliams-dot/quickhealth.git"
APP_DIR="/opt/quickhealth"
APP_USER="quickhealth"
SERVICE_NAME="quickhealth"
SERVICE_FILE="/etc/systemd/system/quickhealth.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo: sudo bash setup.sh" >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify Linux distribution from /etc/os-release." >&2
  exit 1
fi

# This setup guide targets Ubuntu Server 24.04; allow Debian as a close match.
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" && "${ID:-}" != "debian" ]]; then
  echo "This installer supports Ubuntu or Debian only. Detected: ${ID:-unknown}." >&2
  exit 1
fi

if [[ -e "${APP_DIR}/.git" || -n "$(find "${APP_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || true)" ]]; then
  echo "${APP_DIR} already exists and is not empty; refusing to overwrite it." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git python3 python3-venv python3-pip ca-certificates

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --no-create-home --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
fi

install -d -o "${APP_USER}" -g "${APP_USER}" "${APP_DIR}"
git clone --depth 1 --branch main "${REPO_URL}" "${APP_DIR}"

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/.venv/bin/python" -m pip install -r "${APP_DIR}/requirements.txt"

install -d -o "${APP_USER}" -g "${APP_USER}" "${APP_DIR}/data"
if [[ ! -e "${APP_DIR}/.env" ]]; then
  install -o "${APP_USER}" -g "${APP_USER}" -m 0600 \
    "${APP_DIR}/deploy/aws/quickhealth.env.template" "${APP_DIR}/.env"
fi
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
chmod 0600 "${APP_DIR}/.env"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

install -o root -g root -m 0644 \
  "${APP_DIR}/deploy/aws/quickhealth.service" "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

echo "QuickHealth service installed and started."
echo "Enter the real values by hand in ${APP_DIR}/.env, then run: sudo systemctl restart ${SERVICE_NAME}"
echo "Check it with: sudo systemctl status ${SERVICE_NAME} --no-pager"
