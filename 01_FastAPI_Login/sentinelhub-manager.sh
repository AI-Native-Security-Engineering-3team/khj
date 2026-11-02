#!/usr/bin/env bash
# SentinelHub FastAPI 로그인 실습 - 관리 메뉴
# 이 파일을 main.py/create_user.py와 같은 폴더에 둡니다.
set -u

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
VENV_PYTHON="$APP_DIR/.venv/bin/python"
DATA_DIR="$APP_DIR/data"
PID_FILE="$DATA_DIR/uvicorn.pid"
SERVER_LOG="$DATA_DIR/uvicorn.log"
SECURITY_LOG="/var/log/sentinelhub/security-events.jsonl"
HOST="127.0.0.1"  # 추후 Nginx 연동 후에는 127.0.0.1로 변경 권장
PORT="8000"

pause_menu() {
    printf '\n계속하려면 Enter를 누르세요...'
    read -r _ || true
}

check_project() {
    if [[ ! -f "$APP_DIR/main.py" || ! -f "$APP_DIR/create_user.py" ]]; then
        echo "[오류] main.py와 create_user.py가 있는 프로젝트 폴더에 이 파일을 넣으세요."
        return 1
    fi
    if [[ ! -x "$VENV_PYTHON" ]]; then
        echo "[오류] .venv를 찾지 못했습니다. README의 가상환경 설치 과정을 먼저 완료하세요."
        return 1
    fi
    return 0
}

prepare_data() {
    mkdir -p -- "$DATA_DIR" || return 1
    chmod 700 -- "$DATA_DIR" || return 1
    return 0
}

# PID 파일이 있어도 PID 재사용 등의 이유로 다른 프로세스를 종료하지 않도록 검증합니다.
managed_server_running() {
    [[ -f "$PID_FILE" ]] || return 1
    local pid cmd cwd
    IFS= read -r pid < "$PID_FILE" || return 1
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$pid" 2>/dev/null || return 1
    [[ -r "/proc/$pid/cmdline" ]] || return 1
    cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline")" || return 1
    cwd="$(readlink -f -- "/proc/$pid/cwd" 2>/dev/null)" || return 1
    [[ "$cwd" == "$APP_DIR" && "$cmd" == *"uvicorn main:app"* ]]
}

port_in_use() {
    (echo > "/dev/tcp/127.0.0.1/$PORT") >/dev/null 2>&1
}

start_server() {
    check_project || return
    prepare_data || return
    if managed_server_running; then
        echo "[안내] 이 메뉴로 실행한 웹서버가 이미 동작 중입니다. PID: $(cat "$PID_FILE")"
        return
    fi
    if port_in_use; then
        echo "[오류] $PORT 포트가 이미 사용 중입니다. 다른 터미널에서 서버가 실행 중인지 확인하세요."
        return
    fi
    rm -f -- "$PID_FILE"
    touch -- "$SERVER_LOG" || return
    chmod 600 -- "$SERVER_LOG"
    (
        cd -- "$APP_DIR" || exit 1
        nohup "$VENV_PYTHON" -m uvicorn main:app --host "$HOST" --port "$PORT" --workers 1 \
            >> "$SERVER_LOG" 2>&1 < /dev/null &
        echo "$!" > "$PID_FILE"
    )
    sleep 2
    if managed_server_running; then
        echo "[성공] 웹서버가 백그라운드로 실행되었습니다."
        echo "       접속 주소: http://sentinelhub.com:$PORT"
        echo "       PID: $(cat "$PID_FILE")"
        echo "       서버 로그: $SERVER_LOG"
        echo "       메뉴를 종료해도 웹서버는 계속 실행됩니다."
    else
        echo "[오류] 서버 시작에 실패했습니다. 다음 로그를 확인하세요."
        tail -n 15 -- "$SERVER_LOG"
        rm -f -- "$PID_FILE"
    fi
}

stop_server() {
    if ! managed_server_running; then
        echo "[안내] 이 메뉴로 실행한 서버가 없습니다."
        echo "       다른 터미널에서 실행했다면 해당 터미널에서 Ctrl+C로 종료하세요."
        return
    fi
    local pid
    IFS= read -r pid < "$PID_FILE"
    kill "$pid" || return
    echo "[안내] 서버 종료 신호를 보냈습니다. (PID: $pid)"
    for _ in 1 2 3 4 5; do
        if ! managed_server_running; then
            rm -f -- "$PID_FILE"
            echo "[성공] 서버가 종료되었습니다."
            return
        fi
        sleep 1
    done
    echo "[안내] 아직 종료 중입니다. 잠시 후 상태를 다시 확인하세요."
}

server_status() {
    if managed_server_running; then
        echo "[실행 중] 메뉴 관리 서버 PID: $(cat "$PID_FILE")"
    elif port_in_use; then
        echo "[실행 중일 가능성] $PORT 포트가 열려 있으나 이 메뉴가 실행한 서버는 아닙니다."
    else
        echo "[중지됨] $PORT 포트에서 실행 중인 서버가 없습니다."
    fi
    echo "       서버 로그: $SERVER_LOG"
    echo "       보안 로그: $SECURITY_LOG"
}

manage_account() {
    local action="$1" username
    check_project || return
    printf '아이디를 입력하세요: '
    IFS= read -r username || return
    if [[ -z "$username" ]]; then
        echo "[오류] 아이디를 입력해야 합니다."
        return
    fi
    cd -- "$APP_DIR" || return
    if [[ "$action" == 'create' ]]; then
        "$VENV_PYTHON" create_user.py --username "$username"
    else
        "$VENV_PYTHON" create_user.py --username "$username" --reset-password
    fi
}

create_desktop_shortcut() {
    local desktop_dir shortcut
    desktop_dir="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
    if [[ -z "$desktop_dir" || ! -d "$desktop_dir" ]]; then
        desktop_dir="$HOME/Desktop"
    fi
    mkdir -p -- "$desktop_dir" || return
    shortcut="$desktop_dir/SentinelHub-Manager.desktop"
    cat > "$shortcut" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=SentinelHub 관리
Comment=FastAPI 서버 및 계정 관리
Exec="$APP_DIR/sentinelhub-manager.sh"
Icon=utilities-terminal
Terminal=true
Categories=Utility;
DESKTOP
    chmod 755 -- "$shortcut"
    echo "[성공] 바탕화면 바로가기를 생성했습니다: $shortcut"
    echo "       XFCE에서는 최초 실행 시 '실행 허용/신뢰'를 선택해야 할 수 있습니다."
}

show_security_logs() {
    if [[ ! -f "$SECURITY_LOG" ]]; then
        echo "[안내] 보안 로그가 아직 없습니다. 로그인을 시도한 후 확인하세요."
        return
    fi
    echo "----- 최근 보안 이벤트 20건 -----"
    tail -n 20 -- "$SECURITY_LOG"
}

while true; do
    printf '\n=========================================\n'
    printf '      SentinelHub FastAPI 관리 메뉴\n'
    printf '=========================================\n'
    printf '  1. 웹서버 시작 (백그라운드)\n'
    printf '  2. 웹서버 종료\n'
    printf '  3. 웹서버 상태 확인\n'
    printf '  4. 신규 계정 생성\n'
    printf '  5. 기존 계정 비밀번호 변경\n'
    printf '  6. 보안 이벤트 로그 확인\n'
    printf '  7. 바탕화면 실행 아이콘 생성\n'
    printf '  0. 메뉴 종료\n'
    printf '%s\n' '-----------------------------------------'
    printf '번호 선택: '
    IFS= read -r choice || { printf '\n'; break; }
    case "$choice" in
        1) start_server; pause_menu ;;
        2) stop_server; pause_menu ;;
        3) server_status; pause_menu ;;
        4) manage_account create; pause_menu ;;
        5) manage_account reset; pause_menu ;;
        6) show_security_logs; pause_menu ;;
        7) create_desktop_shortcut; pause_menu ;;
        0) echo '메뉴를 종료합니다. 실행 중인 웹서버는 유지됩니다.'; break ;;
        *) echo '[오류] 메뉴 번호를 다시 선택하세요.' ;;
    esac
done
