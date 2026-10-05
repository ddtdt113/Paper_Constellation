Paper Constellation
https://github.com/ddtdt113/Paper_Constellation

== English ==
Run
  macOS:   open "Paper Constellation.app". The app is not signed, so the first time
           right-click it and choose Open, or run:
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
  macOS:   "Paper Constellation.app"을 엽니다. 서명되지 않은 앱이라 처음에는 앱을
           오른쪽 클릭 → 열기를 누르거나, 터미널에서 다음을 실행하세요.
           xattr -dr com.apple.quarantine "Paper Constellation.app"
  Windows: "Paper Constellation" 폴더의 "Paper Constellation.exe"를 실행합니다.
           SmartScreen 경고가 뜨면 추가 정보 → 실행을 누르세요.
  Linux:   "Paper Constellation/Paper Constellation"을 실행합니다. Qt 데스크톱 라이브러리
           (Debian/Ubuntu 기준 libegl1, libxkbcommon-x11-0, libxcb-cursor0 등)가 필요합니다.

라이선스
  Paper Constellation은 Apache-2.0입니다 (LICENSE, NOTICE).
  이 빌드에는 LGPL-3.0인 PySide6 / Qt가 포함되어 있습니다 (LGPL-3.0.txt, GPL-3.0.txt).
  Qt 라이브러리는 앱 폴더 안의 일반 공유 라이브러리이며 교체할 수 있습니다.
