Paper Constellation
https://github.com/ddtdt113/Paper_Constellation

== English ==
Run
  macOS:   open "Paper Constellation.app". The app is not notarized, so the first launch
           is blocked. Click Done, then System Settings -> Privacy & Security ->
           "Open Anyway". Or run once in Terminal:
           xattr -dr com.apple.quarantine "Paper Constellation.app"
  Windows: open the "Paper Constellation" folder and run "Paper Constellation.exe".
           If SmartScreen warns, choose More info -> Run anyway.
  Linux:   run "Paper Constellation/Paper Constellation". Needs the usual Qt desktop
           libraries (e.g. libegl1, libxkbcommon-x11-0, libxcb-cursor0 on Debian/Ubuntu).

Licenses
  Paper Constellation is licensed under Apache-2.0 (LICENSE, NOTICE).
  This build bundles PySide6 / Qt, licensed under LGPL-3.0 (LGPL-3.0.txt, GPL-3.0.txt).
  The Qt libraries are ordinary shared libraries in the app folder and can be replaced.
  Qt source code: https://code.qt.io  PySide6 source: https://code.qt.io/cgit/pyside/pyside-setup.git

== 한국어 ==
실행
  macOS:   "Paper Constellation.app"을 엽니다. 공증받지 않은 앱이라 처음 실행이 막히면
           완료를 누르고 시스템 설정 → 개인정보 보호 및 보안 → "그래도 열기"를 누르거나,
           터미널에서 한 번 실행하세요.
           xattr -dr com.apple.quarantine "Paper Constellation.app"
  Windows: "Paper Constellation" 폴더의 "Paper Constellation.exe"를 실행합니다.
           SmartScreen 경고가 뜨면 추가 정보 → 실행을 누르세요.
  Linux:   "Paper Constellation/Paper Constellation"을 실행합니다. Qt 데스크톱 라이브러리
           (Debian/Ubuntu 기준 libegl1, libxkbcommon-x11-0, libxcb-cursor0 등)가 필요합니다.

라이선스
  Paper Constellation은 Apache-2.0입니다 (LICENSE, NOTICE).
  이 빌드에는 LGPL-3.0인 PySide6 / Qt가 포함되어 있습니다 (LGPL-3.0.txt, GPL-3.0.txt).
  Qt 라이브러리는 앱 폴더 안의 일반 공유 라이브러리이며 교체할 수 있습니다.
