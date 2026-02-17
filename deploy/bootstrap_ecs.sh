#!/usr/bin/env bash
set -euo pipefail

# One-click bootstrap for ECS (Ubuntu/Debian/RHEL-like)
# - Installs system deps
# - Deploys repo to /opt/oneearth
# - Creates venv + installs requirements
# - Performs interactive Earth Engine auth (as alphaearth user)
# - Installs/starts systemd service
# - Configures nginx reverse proxy; optionally obtains HTTPS cert via certbot

usage() {
  cat <<'EOF'
Usage:
  sudo bash deploy/bootstrap_ecs.sh -d <domain> [--email <email>] [--with-https]

Args:
  -d, --domain       Domain name for nginx server_name (required)
  --email            Email for certbot registration (required if --with-https)
  --with-https       Run certbot --nginx to obtain/renew HTTPS cert
  --skip-auth        Skip `earthengine authenticate --quiet` step
  --force-auth       Force refresh Earth Engine credentials (passes --force)
  --skip-system      Skip system package installation (nginx/python/rsync)
  --skip-python-deps Skip venv creation + pip install (fast re-run)
  --dry-run          Print actions without making changes

Notes:
  - DNS for <domain> must already point to this ECS public IP before --with-https.
  - Interactive auth must be done as the same user running systemd service (alphaearth).
  - On RHEL-like systems (Alibaba Cloud Linux/CentOS/RHEL), nginx typically uses /etc/nginx/conf.d/*.conf.
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

is_ip() {
  local s="$1"
  [[ "$s" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]
}

pkg_install() {
  # Usage: pkg_install pkg1 pkg2 ...
  if command -v apt-get >/dev/null 2>&1; then
    run "apt-get update"
    run "apt-get install -y $*"
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    run "dnf -y makecache"
    run "dnf -y install $*"
    return
  fi

  if command -v yum >/dev/null 2>&1; then
    run "yum -y makecache || true"
    run "yum -y install $*"
    return
  fi

  die "No supported package manager found (apt-get/dnf/yum)."
}

run_as() {
  # Usage: run_as <user> <cmd>
  local user="$1"; shift
  local cmd="$*"

  if command -v sudo >/dev/null 2>&1; then
    run "sudo -u ${user} -H bash -lc '$cmd'"
    return
  fi

  if command -v runuser >/dev/null 2>&1; then
    run "runuser -u ${user} -- bash -lc '$cmd'"
    return
  fi

  if command -v su >/dev/null 2>&1; then
    run "su - ${user} -s /bin/bash -c '$cmd'"
    return
  fi

  die "Cannot switch user (need sudo/runuser/su)."
}

pick_python() {
  # Prefer a modern Python for Streamlit (>=3.9).
  local candidates=(python3.11 python3.10 python3.9 python3.8 python3)
  local c
  for c in "${candidates[@]}"; do
    if command -v "$c" >/dev/null 2>&1; then
      local ok
      ok="$($c -c 'import sys; print(int(sys.version_info >= (3,9)))' 2>/dev/null || echo 0)"
      if [[ "$ok" == "1" ]]; then
        echo "$c"
        return 0
      fi
    fi
  done
  echo "python3"
  return 0
}

is_root() {
  [[ "${EUID:-$(id -u)}" -eq 0 ]]
}

DOMAIN=""
EMAIL=""
WITH_HTTPS=0
SKIP_AUTH=0
FORCE_AUTH=0
SKIP_SYSTEM=0
SKIP_PY_DEPS=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--domain)
      DOMAIN="${2:-}"; shift 2 ;;
    --email)
      EMAIL="${2:-}"; shift 2 ;;
    --with-https)
      WITH_HTTPS=1; shift ;;
    --skip-auth)
      SKIP_AUTH=1; shift ;;
    --force-auth)
      FORCE_AUTH=1; shift ;;
    --skip-system)
      SKIP_SYSTEM=1; shift ;;
    --skip-python-deps)
      SKIP_PY_DEPS=1; shift ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      die "unknown arg: $1" ;;
  esac
done

[[ -n "$DOMAIN" ]] || { usage; die "--domain is required"; }
if [[ $WITH_HTTPS -eq 1 && -z "$EMAIL" ]]; then
  usage
  die "--email is required when --with-https is set"
fi

if [[ $WITH_HTTPS -eq 1 ]] && is_ip "$DOMAIN"; then
  die "--with-https requires a real domain name (certbot cannot issue for a bare IP)."
fi

is_root || die "Please run as root (sudo)."

REPO_DIR="$(pwd)"
if [[ ! -f "$REPO_DIR/app.py" || ! -f "$REPO_DIR/requirements.txt" ]]; then
  die "Run this script from the repo root (where app.py and requirements.txt exist)."
fi

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "+ $*"
  else
    eval "$@"
  fi
}

echo "==> Installing system packages"
if [[ $SKIP_SYSTEM -eq 0 ]]; then
  pkg_install python3 python3-pip nginx rsync
else
  echo "==> Skipping system packages (--skip-system)"
fi

# Try to ensure a modern Python exists (best-effort for RHEL-like).
if [[ $SKIP_SYSTEM -eq 0 ]] && ! command -v python3.11 >/dev/null 2>&1; then
  if command -v dnf >/dev/null 2>&1; then
    run "dnf -y install python3.11 python3.11-pip || true"
  elif command -v yum >/dev/null 2>&1; then
    run "yum -y install python3.11 python3.11-pip || true"
  fi
fi

PYTHON_BIN="$(pick_python)"
echo "==> Using Python: $PYTHON_BIN ($($PYTHON_BIN -c 'import sys; print(sys.version.split()[0])'))"

# Some distros split venv into a separate package; others bundle it in Python.
if "$PYTHON_BIN" -c 'import venv' >/dev/null 2>&1; then
  echo "==> Python venv module: OK"
else
  echo "==> Python venv module missing; trying to install venv/virtualenv packages"
  # Best-effort: these package names vary by distro.
  if command -v dnf >/dev/null 2>&1; then
    run "dnf -y install python3-venv || dnf -y install python3-virtualenv || true"
  elif command -v yum >/dev/null 2>&1; then
    run "yum -y install python3-venv || yum -y install python3-virtualenv || true"
  else
    run "apt-get install -y python3-venv || true"
  fi

  if ! "$PYTHON_BIN" -c 'import venv' >/dev/null 2>&1; then
    echo "==> Still no venv module; will use virtualenv via pip"
    run "$PYTHON_BIN -m pip install -U pip virtualenv"
  fi
fi

if [[ $WITH_HTTPS -eq 1 ]]; then
  # Note: some RHEL-like distros may require enabling EPEL for certbot packages.
  pkg_install certbot python3-certbot-nginx
fi

need_cmd rsync
need_cmd systemctl
need_cmd nginx

echo "==> Creating service user: alphaearth"
run "useradd -m -s /bin/bash alphaearth || true"

echo "==> Preparing directories"
run "mkdir -p /opt/oneearth /var/log/alphaearth /etc/alphaearth"
run "chown -R alphaearth:alphaearth /opt/oneearth /var/log/alphaearth"

echo "==> Deploying code to /opt/oneearth"
# Use rsync to keep /opt/oneearth in sync with repo root
run "rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '*.log' \
  --exclude '.pytest_cache' \
  '$REPO_DIR/' /opt/oneearth/"
run "chown -R alphaearth:alphaearth /opt/oneearth"

echo "==> Preparing Streamlit home config under /opt/oneearth"
run "mkdir -p /opt/oneearth/.streamlit"
run "touch /opt/oneearth/.streamlit/secrets.toml"
run "chmod 600 /opt/oneearth/.streamlit/secrets.toml"

# Ensure Streamlit won't try to read /home/<user>/.streamlit/secrets.toml under systemd.
# The repo should include .streamlit/config.toml, but we enforce the secrets path here
# to make reruns safe even if the deployed file is older.
if [[ ! -f /opt/oneearth/.streamlit/config.toml ]]; then
  run "cat > /opt/oneearth/.streamlit/config.toml <<'EOF'
[server]
address = \"127.0.0.1\"
port = 8501
headless = true

[browser]
gatherUsageStats = false

[secrets]
files = [\"/opt/oneearth/.streamlit/secrets.toml\"]
EOF"
fi

if ! grep -q "^\[secrets\]" /opt/oneearth/.streamlit/config.toml \
  || ! grep -q "/opt/oneearth/.streamlit/secrets.toml" /opt/oneearth/.streamlit/config.toml; then
  run "cat >> /opt/oneearth/.streamlit/config.toml <<'EOF'

[secrets]
files = [\"/opt/oneearth/.streamlit/secrets.toml\"]
EOF"
fi

run "chown -R alphaearth:alphaearth /opt/oneearth/.streamlit"

echo "==> Creating environment file (if missing)"
if [[ ! -f /etc/alphaearth/alphaearth.env ]]; then
  run "cp /opt/oneearth/deploy/alphaearth.env.example /etc/alphaearth/alphaearth.env"
fi
run "chown -R root:root /etc/alphaearth"
run "chmod 600 /etc/alphaearth/alphaearth.env || true"

echo "==> Creating Python venv + installing deps"
REQ_SHA="$(sha256sum "$REPO_DIR/requirements.txt" | awk '{print $1}')"

if [[ $SKIP_PY_DEPS -eq 1 ]]; then
  echo "==> Skipping python deps (--skip-python-deps)"
else
  # If venv exists and requirements unchanged, skip pip install for faster reruns.
  if [[ -x /opt/oneearth/.venv/bin/python && -f /opt/oneearth/.venv/.requirements.sha256 ]]; then
    OLD_SHA="$(cat /opt/oneearth/.venv/.requirements.sha256 || true)"
  else
    OLD_SHA=""
  fi

  if [[ -x /opt/oneearth/.venv/bin/python && "$OLD_SHA" == "$REQ_SHA" ]]; then
    echo "==> requirements.txt unchanged; reusing existing venv"
  else
    run_as alphaearth "cd /opt/oneearth && rm -rf .venv"
    if "$PYTHON_BIN" -c 'import venv' >/dev/null 2>&1; then
      run_as alphaearth "cd /opt/oneearth && $PYTHON_BIN -m venv .venv"
    else
      run_as alphaearth "cd /opt/oneearth && $PYTHON_BIN -m virtualenv .venv"
    fi
    run_as alphaearth "cd /opt/oneearth && ./.venv/bin/python -m pip install -U pip setuptools wheel"
    run_as alphaearth "cd /opt/oneearth && ./.venv/bin/python -m pip install -r requirements.txt"
    run_as alphaearth "cd /opt/oneearth && echo '$REQ_SHA' > ./.venv/.requirements.sha256"
  fi
fi

if [[ $SKIP_AUTH -eq 0 ]]; then
  echo "==> Earth Engine interactive auth (alphaearth user)"
  echo "    You will get a URL. Open it on your local computer and paste the code back here."
  AUTH_FORCE_FLAG=""
  if [[ $FORCE_AUTH -eq 1 ]]; then
    AUTH_FORCE_FLAG="--force"
  fi
  run_as alphaearth "cd /opt/oneearth && if [[ -x ./.venv/bin/earthengine ]]; then ./.venv/bin/earthengine authenticate --quiet --auth_mode=notebook ${AUTH_FORCE_FLAG}; else earthengine authenticate --quiet --auth_mode=notebook ${AUTH_FORCE_FLAG}; fi"
else
  echo "==> Skipping Earth Engine auth (--skip-auth)"
fi

echo "==> Validating Earth Engine initialization (alphaearth user)"
set +e
run_as alphaearth "cd /opt/oneearth && ./.venv/bin/python -c \"import ee; ee.Initialize(); print(\\\"Earth Engine: Initialize OK\\\")\""
EE_INIT_RC=$?
set -e
if [[ $EE_INIT_RC -ne 0 ]]; then
  cat <<'EOF' >&2
ERROR: Earth Engine initialization failed for the service user.

Most common fixes:
  1) Re-run auth as the same user that runs systemd (alphaearth):
     sudo -u alphaearth -H /opt/oneearth/.venv/bin/earthengine authenticate --quiet --auth_mode=notebook --force
  2) Restart the service:
     sudo systemctl restart alphaearth

Alternative (production): use a service account by setting EE_SERVICE_ACCOUNT and EE_PRIVATE_KEY_FILE in /etc/alphaearth/alphaearth.env.
EOF
  if [[ $SKIP_AUTH -eq 0 ]]; then
    exit 1
  fi
fi

echo "==> Installing systemd service"
run "cp /opt/oneearth/deploy/alphaearth.service /etc/systemd/system/alphaearth.service"
run "systemctl daemon-reload"
run "systemctl enable --now alphaearth"
run "systemctl restart alphaearth || true"

echo "==> Configuring nginx reverse proxy (HTTP)"
if [[ -d /etc/nginx/sites-available ]]; then
  run "cp /opt/oneearth/deploy/nginx-alphaearth.conf /etc/nginx/sites-available/alphaearth"
  run "sed -i 's/YOUR_DOMAIN_NAME/${DOMAIN}/g' /etc/nginx/sites-available/alphaearth"
  run "ln -sf /etc/nginx/sites-available/alphaearth /etc/nginx/sites-enabled/alphaearth"
else
  run "cp /opt/oneearth/deploy/nginx-alphaearth.conf /etc/nginx/conf.d/alphaearth.conf"
  run "sed -i 's/YOUR_DOMAIN_NAME/${DOMAIN}/g' /etc/nginx/conf.d/alphaearth.conf"
fi
run "nginx -t"
if systemctl is-active --quiet nginx; then
  run "systemctl reload nginx || systemctl restart nginx"
else
  run "systemctl enable --now nginx"
fi

if [[ $WITH_HTTPS -eq 1 ]]; then
  echo "==> Obtaining HTTPS certificate via certbot"
  echo "    Domain: $DOMAIN"
  echo "    Email:  $EMAIL"
  run "certbot --nginx -d '${DOMAIN}' -m '${EMAIL}' --agree-tos --non-interactive"
  run "systemctl reload nginx"
fi

echo "==> Done"
if [[ $WITH_HTTPS -eq 1 ]]; then
  echo "Open: https://${DOMAIN}/"
else
  echo "Open: http://${DOMAIN}/"
fi

echo "Service status:"
run "systemctl status alphaearth --no-pager || true"

echo "Tail logs:"
run "tail -n 50 /var/log/alphaearth/streamlit.log || true"
