@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 949 >nul
title SentinelHub - Web Detection Demo v1.0

rem Fixed target: approved SentinelHub internal LAN web server only.
rem Only GET requests; no login attempts, exploits, writes, or high-rate traffic.
set "TARGET_IP=192.168.0.4"
set "DOMAIN=sentinelhub.com"
set "BASE_URL=http://%DOMAIN%"
set "RESOLVE=%DOMAIN%:80:%TARGET_IP%"

where curl.exe >nul 2>&1
if errorlevel 1 (
    echo [오류] curl.exe를 찾을 수 없습니다.
    echo Windows 10/11 기본 curl.exe가 필요합니다.
    pause
    exit /b 1
)

:MENU
cls
echo ==================================================
echo       SentinelHub 웹 보안 탐지 시연 v1.0
echo ==================================================
echo   대상 : %DOMAIN% ^(%TARGET_IP%:80^)
echo   방식 : HTTP GET / 탐지 기록 확인용 / 차단 없음
echo --------------------------------------------------
echo   [1] 서버 연결 확인 ^(1회^)
echo   [2] 민감 경로 접근 시연 ^(1회^)
echo   [3] 비정상 URL 반복 탐색 ^(서로 다른 404 5회^)
echo   [4] SQLi 의심 문자열 시연 ^(1회^)
echo   [5] XSS 의심 문자열 시연 ^(1회^)
echo   [6] 전체 자동 시연 ^(8회 + 연결 확인 1회^)
echo   [0] 종료
echo --------------------------------------------------
echo   주의: 의심 이벤트는 실습용이며 실제 침해가 아닙니다.
echo ==================================================
choice /c 1234560 /n /m "번호 선택: "
if errorlevel 7 goto QUIT
if errorlevel 6 goto DEMO_ALL
if errorlevel 5 goto DEMO_XSS
if errorlevel 4 goto DEMO_SQLI
if errorlevel 3 goto DEMO_404
if errorlevel 2 goto DEMO_SENSITIVE
if errorlevel 1 goto DEMO_HEALTH
goto MENU

:DEMO_HEALTH
call :CHECK_SERVER
goto DONE

:DEMO_SENSITIVE
call :CHECK_SERVER
if errorlevel 1 goto DONE
call :SEND "민감 경로 접근(.env)" "/.env" "404"
goto DONE

:DEMO_404
call :CHECK_SERVER
if errorlevel 1 goto DONE
call :FIVE_NOT_FOUND
goto DONE

:DEMO_SQLI
call :CHECK_SERVER
if errorlevel 1 goto DONE
rem Inert query text; /api/health never executes the string as SQL.
call :SEND "SQLi 의심 문자열(비실행 GET 쿼리)" "/api/health?q=UNION+SELECT" "200"
goto DONE

:DEMO_XSS
call :CHECK_SERVER
if errorlevel 1 goto DONE
rem Inert query text; /api/health never renders this as HTML or JS.
call :SEND "XSS 의심 문자열(비실행 GET 쿼리)" "/api/health?q=javascript:demo" "200"
goto DONE

:DEMO_ALL
call :CHECK_SERVER
if errorlevel 1 goto DONE
echo.
echo [전체 시연] 최대 8회 GET 요청을 순서대로 전송합니다.
call :SEND "민감 경로 접근(.env)" "/.env" "404"
if errorlevel 1 goto DONE
call :FIVE_NOT_FOUND
if errorlevel 1 goto DONE
call :SEND "SQLi 의심 문자열(비실행 GET 쿼리)" "/api/health?q=UNION+SELECT" "200"
if errorlevel 1 goto DONE
call :SEND "XSS 의심 문자열(비실행 GET 쿼리)" "/api/health?q=javascript:demo" "200"
goto DONE

:CHECK_SERVER
echo.
echo [연결 검사] %DOMAIN% -^> %TARGET_IP%:80
curl.exe -fsS --globoff --noproxy "*" --resolve "%RESOLVE%" --connect-timeout 3 --max-time 8 --user-agent "SentinelHub-Detection-Demo/1.0" -o NUL -w "  HTTP %%{http_code}\n" "%BASE_URL%/api/health"
if errorlevel 1 (
    echo [중단] 서버가 응답하지 않거나 /api/health가 정상 상태가 아닙니다.
    exit /b 1
)
exit /b 0

:FIVE_NOT_FOUND
echo.
echo [404 반복 탐지] 존재하지 않는 고유 경로 5개를 요청합니다.
for /L %%N in (1,1,5) do (
    call :SEND "없는 경로 %%N/5" "/__sentinelhub_demo_missing_0%%N__" "404"
    if errorlevel 1 exit /b 1
    if not "%%N"=="5" timeout /t 1 /nobreak >nul
)
exit /b 0

:SEND
echo.
echo [요청] %~1  ^(예상 HTTP %~3^)
curl.exe -sS --globoff --noproxy "*" --resolve "%RESOLVE%" --connect-timeout 3 --max-time 8 --user-agent "SentinelHub-Detection-Demo/1.0" -H "Cache-Control: no-cache" -o NUL -w "  HTTP %%{http_code}\n" "%BASE_URL%%~2"
if errorlevel 1 (
    echo [중단] HTTP 요청에 실패했습니다. 이후 요청은 전송하지 않습니다.
    exit /b 1
)
exit /b 0

:DONE
echo.
echo --------------------------------------------------
echo 확인: Grafana의 통합 로그 / 기존 로그 패널을 확인하세요.
echo 동일 IP+동일 규칙은 60초 중복 기록 억제가 적용됩니다.
echo 응답 코드가 예상과 달랐다면 서버 상태를 확인하세요.
echo --------------------------------------------------
echo 아무 키나 누르면 메뉴로 돌아갑니다.
pause >nul
goto MENU

:QUIT
endlocal
exit /b 0
