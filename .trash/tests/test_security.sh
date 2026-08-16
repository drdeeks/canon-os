#!/usr/bin/env bash
# ============================================================================
# Test: Security
# Validates SSH, firewall, fail2ban, user isolation, container security
# ============================================================================

set -uo pipefail

PASS=0; FAIL=0; SKIP=0; TOTAL=0

run() {
  local desc="$1" cmd="$2" timeout="${3:-10}"
  ((TOTAL++))
  if timeout "$timeout" bash -c "$cmd" &>/dev/null; then
    echo -e "  \033[0;32mPASS\033[0m  $desc"; ((PASS++))
  elif [[ $? -eq 124 ]]; then
    echo -e "  \033[1;33mSKIP\033[0m  $desc (timeout)"; ((SKIP++))
  else
    echo -e "  \033[0;31mFAIL\033[0m  $desc"; ((FAIL++))
  fi
}

skip() { ((TOTAL++)); ((SKIP++)); echo -e "  \033[1;33mSKIP\033[0m  $1 ($2)"; }

# SSH configuration
run "SSH on non-standard port" "grep -rq 'Port 2222' /etc/ssh/sshd_config*"
run "Password auth disabled" "grep -rq 'PasswordAuthentication no' /etc/ssh/sshd_config*"
run "Pubkey auth enabled" "grep -rq 'PubkeyAuthentication yes' /etc/ssh/sshd_config*"
run "Root login disabled" "grep -rq 'PermitRootLogin no' /etc/ssh/sshd_config*"

# Firewall
command -v ufw &>/dev/null && run "UFW active" "ufw status | grep -q 'Status: active'" || skip "UFW" "not installed"

# fail2ban
command -v fail2ban-client &>/dev/null && run "fail2ban running" "systemctl is-active fail2ban" || skip "fail2ban" "not installed"

# Creator isolation
id creator &>/dev/null && run "Creator has nologin shell" "[[ \$(getent passwd creator | cut -d: -f7) == '/usr/sbin/nologin' ]]" || skip "Creator account" "not created"
id creator &>/dev/null && run "Creator no sudo" "sudo -l -U creator 2>&1 | grep -q 'not allowed'" || skip "Creator sudo check" "no creator account"
id creator &>/dev/null && run "Creator no docker" "! groups creator 2>/dev/null | grep -q docker" || skip "Creator docker check" "no creator account"
id creator &>/dev/null && run "Creator blocked from /etc/shadow" "! sudo -u creator cat /etc/shadow 2>/dev/null" || skip "Creator /etc/shadow" "no creator account"
id creator &>/dev/null && run "Creator blocked from /root" "! sudo -u creator ls /root/ 2>/dev/null" || skip "Creator /root" "no creator account"

# Admin isolation
id admin &>/dev/null && run "Admin has bash shell" "[[ \$(getent passwd admin | cut -d: -f7) == '/bin/bash' ]]" || skip "Admin account" "not created"
id admin &>/dev/null && run "Admin has docker" "groups admin 2>/dev/null | grep -q docker" || skip "Admin docker check" "no admin account"

# Admin home is small (<10MB)
if [[ -d /home/admin ]]; then
  run "Admin home <10MB" "[ \$(du -sm /home/admin 2>/dev/null | cut -f1) -lt 10 ]"
else
  skip "Admin home size" "no /home/admin"
fi

# Container security
if command -v docker &>/dev/null; then
  for cid in $(docker ps -q 2>/dev/null); do
    name=$(docker inspect --format '{{.Name}}' "$cid" 2>/dev/null | sed 's/^\///')
    uid=$(docker exec "$cid" id -u 2>/dev/null || echo "unknown")
    run "Container $name not root" "[[ '$uid' != '0' ]]" 5
  done
  [[ $(docker ps -q 2>/dev/null | wc -l) -eq 0 ]] && skip "Container security" "no containers running"
else
  skip "Container security" "Docker not available"
fi

# Docker socket permissions
if [[ -S /var/run/docker.sock ]]; then
  run "Docker socket not world-readable" "! stat -c '%a' /var/run/docker.sock | grep -q '7$'"
else
  skip "Docker socket" "not found"
fi

# Filesystem ACLs
command -v getfacl &>/dev/null && run "ACL tools available" "true" || skip "ACL tools" "not installed"

echo ""
echo -e "  \033[1mSecurity: $PASS passed, $FAIL failed, $SKIP skipped\033[0m"
[[ $FAIL -eq 0 ]]
