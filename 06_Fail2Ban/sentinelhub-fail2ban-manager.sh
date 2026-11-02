#!/usr/bin/env bash
# SentinelHub Fail2Ban Manager v1.0.0
# Kali Linux | Bash | UTF-8
# 기존 jail 설정을 변경하지 않는 대화형 관리 도구입니다.
# 메뉴 5(수동 차단), 4(차단 해제), 8(서비스 재시작)는 명시적 사용자 확인 후 실행됩니다.
# 중요: 스크립트 자체는 Fail2Ban의 자동 차단에서 관리자 IP를 보호하지 않습니다.
#       실제 자동 차단 방지용 ignoreip는 별도 설정·검증해야 합니다.

set -u
set -o pipefail
export LC_ALL=C

readonly VERSION='1.0.0'
readonly ADMIN_IP='192.168.0.3'      # SentinelHub 관리자 Windows PC
readonly SERVER_IP='192.168.0.4'     # SentinelHub Kali VM

SUDO=()
JAILS=()
BANNED_IPS=()
SELECTED_JAIL=''

if (( EUID != 0 )); then
  SUDO=(sudo)
fi

f2b() { "${SUDO[@]}" fail2ban-client "$@"; }
systemctl_admin() { "${SUDO[@]}" systemctl "$@"; }
journalctl_admin() { "${SUDO[@]}" journalctl "$@"; }

line() { printf '%s\n' '------------------------------------------------------------'; }
info() { printf '[안내] %s\n' "$*"; }
warn() { printf '[주의] %s\n' "$*"; }
err()  { printf '[오류] %s\n' "$*" >&2; }

pause_menu() {
  printf '\n'
  read -r -p '메뉴로 돌아가려면 Enter를 누르세요... ' _ || true
}

require_exact_confirmation() {
  local expected="$1" prompt="$2" answer=''
  read -r -p "$prompt [$expected 입력]: " answer || return 1
  [[ "$answer" == "$expected" ]]
}

is_ip() {
  # 입력은 Python 인수로만 전달되며 셸 명령으로 평가되지 않습니다.
  python3 - "$1" <<'PY'
import ipaddress, sys
try:
    ipaddress.ip_address(sys.argv[1])
except ValueError:
    sys.exit(1)
PY
}

is_protected_ip() {
  python3 - "$1" "$ADMIN_IP" "$SERVER_IP" <<'PY'
import ipaddress, sys
ip = ipaddress.ip_address(sys.argv[1])
if getattr(ip, 'ipv4_mapped', None):
    ip = ip.ipv4_mapped
protected = {ipaddress.ip_address(s) for s in sys.argv[2:]}
sys.exit(0 if ip in protected or ip.is_loopback or ip.is_unspecified else 1)
PY
}

is_ignored_in_jail() {
  local jail="$1" ip="$2" raw
  raw="$(f2b get "$jail" ignoreip 2>/dev/null)" || return 2
  python3 - "$ip" "$raw" <<'PY'
import ipaddress, re, sys
addr = ipaddress.ip_address(sys.argv[1])
if getattr(addr, 'ipv4_mapped', None):
    addr = addr.ipv4_mapped
# Fail2Ban 버전에 따라 출력 구분자가 달라질 수 있으므로 IP/CIDR만 판독합니다.
for token in re.split(r"[\s,;\[\]\(\)\{\}'\"]+", sys.argv[2]):
    if not token:
        continue
    try:
        network = ipaddress.ip_network(token, strict=False)
        if network.version == addr.version and addr in network:
            sys.exit(0)
    except ValueError:
        continue
sys.exit(1)
PY
}

extract_ips() {
  python3 -c '
import ipaddress, re, sys
seen=set()
for token in re.split(r"[\s,;\[\]\(\)\{\}\x27\"]+", sys.stdin.read()):
    try:
        ip=str(ipaddress.ip_address(token))
    except ValueError:
        continue
    if ip not in seen:
        seen.add(ip)
        print(ip)
'
}

load_jails() {
  local output
  output="$(f2b status 2>&1)" || { err "Jail 목록 조회 실패: $output"; return 1; }
  mapfile -t JAILS < <(
    printf '%s\n' "$output" |
      sed -n 's/.*Jail list:[[:space:]]*//p' |
      tr ',' '\n' |
      sed 's/^[[:space:]]*//;s/[[:space:]]*$//;/^$/d'
  )
  return 0
}

pick_jail() {
  local n i
  SELECTED_JAIL=''
  load_jails || return 1
  if (( ${#JAILS[@]} == 0 )); then
    warn '활성 Jail이 없습니다.'
    return 1
  fi
  printf '\n[활성 Jail 목록]\n'
  for i in "${!JAILS[@]}"; do
    printf '  %d) %s\n' "$((i + 1))" "${JAILS[$i]}"
  done
  read -r -p 'Jail 번호 선택 (0: 취소): ' n || return 1
  [[ "$n" =~ ^[0-9]+$ ]] || { err '숫자로 입력해 주세요.'; return 1; }
  n=$((10#$n))
  (( n >= 1 && n <= ${#JAILS[@]} )) || return 1
  SELECTED_JAIL="${JAILS[$((n - 1))]}"
  return 0
}

load_banned_ips() {
  local raw
  BANNED_IPS=()
  raw="$(f2b get "$1" banip 2>&1)" || {
    err "차단 IP 조회 실패: $raw"
    return 1
  }
  mapfile -t BANNED_IPS < <(printf '%s\n' "$raw" | extract_ips)
  return 0
}

show_service() {
  line
  printf 'Fail2Ban 서비스 상태\n'
  line
  systemctl_admin status fail2ban --no-pager -l || true
  printf '\nFail2Ban 응답 확인: '
  f2b ping || true
}

show_jails() {
  line
  printf '활성 Jail 목록\n'
  line
  f2b status || true
}

show_jail_details() {
  pick_jail || return 0
  line
  printf '[%s] 상세 상태\n' "$SELECTED_JAIL"
  line
  f2b status "$SELECTED_JAIL" || true
  printf '\n[현재 차단 IP]\n'
  f2b get "$SELECTED_JAIL" banip || true
  printf '\n[정책 정보]\n'
  printf 'findtime: '; f2b get "$SELECTED_JAIL" findtime || true
  printf 'maxretry: '; f2b get "$SELECTED_JAIL" maxretry || true
  printf 'bantime : '; f2b get "$SELECTED_JAIL" bantime || true
}

unban_one() {
  local num ip i
  pick_jail || return 0
  load_banned_ips "$SELECTED_JAIL" || return 0
  if (( ${#BANNED_IPS[@]} == 0 )); then
    info "[$SELECTED_JAIL] 현재 차단된 IP가 없습니다."
    return 0
  fi
  printf '\n[%s] 차단 중인 IP\n' "$SELECTED_JAIL"
  for i in "${!BANNED_IPS[@]}"; do
    printf '  %d) %s\n' "$((i + 1))" "${BANNED_IPS[$i]}"
  done
  read -r -p '해제할 IP 번호 (0: 취소): ' num || return 0
  [[ "$num" =~ ^[0-9]+$ ]] || { err '숫자로 입력해 주세요.'; return 0; }
  num=$((10#$num))
  (( num >= 1 && num <= ${#BANNED_IPS[@]} )) || return 0
  ip="${BANNED_IPS[$((num - 1))]}"
  printf '\n대상 Jail: %s\n차단 해제 대상: %s\n' "$SELECTED_JAIL" "$ip"
  if ! require_exact_confirmation 'UNBAN' '위 IP의 차단을 해제하시겠습니까?'; then
    info '취소했습니다.'
    return 0
  fi
  if f2b set "$SELECTED_JAIL" unbanip "$ip"; then
    info '차단 해제 명령 처리 완료. 현재 상태를 다시 확인합니다.'
    f2b status "$SELECTED_JAIL" || true
  else
    err '차단 해제 명령 실행에 실패했습니다.'
  fi
}

ban_one() {
  local ip result
  pick_jail || return 0
  warn '수동 차단은 실제 방화벽/Fail2Ban 차단 규칙에 즉시 영향을 줄 수 있습니다.'
  warn "관리자 PC($ADMIN_IP), Kali 서버($SERVER_IP), 루프백 주소는 이 도구에서 차단 금지입니다."
  read -r -p '수동 차단할 IP (빈 값: 취소): ' ip || return 0
  [[ -n "$ip" ]] || return 0
  if ! is_ip "$ip"; then
    err '올바른 IPv4 또는 IPv6 주소가 아닙니다.'
    return 0
  fi
  if is_protected_ip "$ip"; then
    err '관리자/서버/루프백 주소는 안전을 위해 수동 차단을 거부합니다.'
    return 0
  fi
  is_ignored_in_jail "$SELECTED_JAIL" "$ip"
  result=$?
  if (( result == 0 )); then
    err 'Jail 예외(ignored) 목록에 포함된 주소입니다. 수동 차단을 거부합니다.'
    return 0
  elif (( result != 1 )); then
    err 'Jail 예외 목록을 검사할 수 없어 안전상 수동 차단을 중단합니다.'
    return 0
  fi
  printf '\nJail: %s\nIP: %s\n' "$SELECTED_JAIL" "$ip"
  if ! require_exact_confirmation 'BAN' '정말 이 IP를 차단하시겠습니까?'; then
    info '취소했습니다.'
    return 0
  fi
  if f2b set "$SELECTED_JAIL" banip "$ip"; then
    info '수동 차단 명령 처리 완료.'
    f2b status "$SELECTED_JAIL" || true
  else
    err '수동 차단 명령 실행에 실패했습니다.'
  fi
}

show_ignoreip() {
  local jail output result
  pick_jail || return 0
  jail="$SELECTED_JAIL"
  printf '\n[%s] 현재 적용된 차단 예외 IP/CIDR\n' "$jail"
  output="$(f2b get "$jail" ignoreip 2>&1)" || {
    err "예외 목록 조회 실패: $output"
    return 0
  }
  printf '%s\n' "$output"
  is_ignored_in_jail "$jail" "$ADMIN_IP"
  result=$?
  if (( result == 0 )); then
    info "관리자 IP $ADMIN_IP 가 예외 IP/CIDR 목록에 포함된 것으로 확인됩니다."
  elif (( result == 1 )); then
    warn "관리자 IP $ADMIN_IP 가 숫자 IP/CIDR 예외 목록에 없습니다!"
    warn 'SSH 실패 테스트/자동 차단 시험 전에 별도의 영구 ignoreip 설정이 필요합니다.'
  else
    warn '예외 상태를 확인하지 못했습니다. SSH 실패 테스트를 진행하지 마세요.'
  fi
  info '이 메뉴는 읽기 전용이며 ignoreip 설정을 변경하지 않습니다.'
}

current_logfile() {
  local target
  target="$(f2b get logtarget 2>/dev/null || true)"
  target="${target//$'\n'/}"
  target="${target//\"/}"
  if [[ "$target" == /* && -f "$target" ]]; then
    printf '%s\n' "$target"
  elif [[ -f '/var/log/fail2ban.log' ]]; then
    printf '%s\n' '/var/log/fail2ban.log'
  else
    printf '\n'
  fi
}

show_logs() {
  local logfile
  logfile="$(current_logfile)"
  printf 'Fail2Ban logtarget: '
  f2b get logtarget || true
  printf '\n[최근 차단·해제 이벤트 후보]\n'
  if [[ -n "$logfile" ]]; then
    "${SUDO[@]}" tail -n 150 "$logfile" | grep -Ei 'Ban |Unban |Restore Ban|Found ' | tail -n 60 || true
    printf '\n[로그 마지막 15줄]\n'
    "${SUDO[@]}" tail -n 15 "$logfile" || true
  else
    info '파일 로그를 찾지 못해 Fail2Ban 서비스 journal을 조회합니다.'
    journalctl_admin -u fail2ban --no-pager -n 80 || true
  fi
}

restart_service() {
  warn 'Fail2Ban 재시작 중 차단 규칙/네트워크 처리에 잠시 영향이 있을 수 있습니다.'
  if ! require_exact_confirmation 'RESTART' 'Fail2Ban 서비스를 재시작할까요?'; then
    info '취소했습니다.'
    return 0
  fi
  if systemctl_admin restart fail2ban; then
    info '재시작 명령 처리 완료.'
    systemctl_admin is-active fail2ban || true
    f2b status || true
  else
    err '재시작에 실패했습니다. 서비스 상태를 확인해 주세요.'
  fi
}

live_logs() {
  local logfile
  logfile="$(current_logfile)"
  printf '실시간 로그 확인 (Ctrl+C로 종료)\n'
  # Ctrl+C 후 관리 메뉴가 종료되지 않도록 일시적인 INT 핸들러를 사용합니다.
  trap 'printf "\n실시간 로그 보기를 종료했습니다.\n"' INT
  if [[ -n "$logfile" ]]; then
    "${SUDO[@]}" tail -n 20 -F "$logfile" || true
  else
    journalctl_admin -u fail2ban --no-pager -f -n 20 || true
  fi
  trap - INT
}

show_menu() {
  clear 2>/dev/null || true
  line
  printf '  SentinelHub Fail2Ban Manager  v%s\n' "$VERSION"
  line
  printf '  1) Fail2Ban 서비스 상태 확인\n'
  printf '  2) 활성 Jail 목록 조회\n'
  printf '  3) Jail 상세 상태 / 차단 IP / 정책 조회\n'
  printf '  4) IP 차단 해제 (선택한 Jail 내 1개)\n'
  printf '  5) IP 수동 차단 (확인 절차 필요)\n'
  printf '  6) 차단 예외 IP(ignoreip) 확인\n'
  printf '  7) 차단·해제 로그 조회\n'
  printf '  8) Fail2Ban 서비스 재시작\n'
  printf '  9) 실시간 Fail2Ban 로그\n'
  printf '  0) 종료\n'
  line
  printf '  중요: 관리자 IP %s 예외 설정은 별도로 필요합니다.\n' "$ADMIN_IP"
  line
}

check_requirements() {
  local cmd
  for cmd in bash fail2ban-client systemctl journalctl python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      err "필수 명령어를 찾을 수 없습니다: $cmd"
      return 1
    fi
  done
  if (( EUID != 0 )); then
    if ! command -v sudo >/dev/null 2>&1; then
      err '관리자 권한 확인용 sudo 명령어가 없습니다.'
      return 1
    fi
    info 'Fail2Ban을 조회·관리하기 위한 sudo 인증을 요청합니다.'
    "${SUDO[@]}" -v || return 1
  fi
  if ! f2b ping >/dev/null 2>&1; then
    err 'Fail2Ban 서비스에 연결할 수 없습니다. systemctl status fail2ban을 확인해 주세요.'
    return 1
  fi
  return 0
}

main() {
  local choice
  if [[ "${1:-}" == '--help' ]]; then
    printf 'SentinelHub Fail2Ban Manager v%s\n사용: bash %s\n' "$VERSION" "${0##*/}"
    printf '실행 시 기존 Jail과 파일을 자동으로 수정하지 않습니다.\n'
    exit 0
  fi
  check_requirements || exit 1
  while true; do
    show_menu
    read -r -p '메뉴 번호를 입력하세요: ' choice || { printf '\n종료합니다.\n'; break; }
    case "$choice" in
      1) show_service; pause_menu ;;
      2) show_jails; pause_menu ;;
      3) show_jail_details; pause_menu ;;
      4) unban_one; pause_menu ;;
      5) ban_one; pause_menu ;;
      6) show_ignoreip; pause_menu ;;
      7) show_logs; pause_menu ;;
      8) restart_service; pause_menu ;;
      9) live_logs; pause_menu ;;
      0) info '프로그램을 종료합니다.'; break ;;
      *) warn '0~9 사이의 번호를 선택해 주세요.'; pause_menu ;;
    esac
  done
}

main "$@"
