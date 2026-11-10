# Rust 도구 빌드와 호환 경로

규칙, 사전, 의미 판정 범위는 유지하며 기존 네 Python 처리기를 Rust로 전환했습니다. native 실행에는 Python이 필요하지 않습니다. 개발 검사와 기존 import API를 쓰려면 Python 3.11 이상이 필요합니다.

## 명시적인 빌드

각 실행 머신에서 저장소 루트로 이동해 빌드합니다. `Cargo.lock`으로 의존성 버전을 고정합니다. 일반 CLI와 Python 어댑터는 빌드하거나 다운로드하지 않습니다.

```bash
cargo build --release --locked
./target/release/dot-stk100 lint --source examples/source.md --candidate examples/candidate.md
./target/release/dot-stk100 evaluate --terminology-examples
./target/release/dot-stk100 render --check
./target/release/dot-stk100 validate
```

`lint-text`, `evaluate-linter`, `render-rules`, `validate-package` 실행 파일도 같은 라이브러리와 CLI 처리를 사용합니다. 기본 실행 파일은 `dot-stk100`입니다. 루트는 실행 파일의 상위 경로에서 찾으며 별도 패키지를 검사하려면 `--root PATH`를 사용합니다.

## 기존 호출과 설치

기존 `python3 scripts/lint_text.py` 등의 네 CLI와 확인한 import API는 같은 native 구현을 호출합니다. 두 구현을 별도로 유지하지 않습니다. 어댑터는 패키지의 `bin/dot-stk100`, 개발 경로인 `target/release/dot-stk100` 순서로 찾습니다. 명시적인 `DOT_STK100_BIN`은 실행 파일 경로를 지정하며 다른 경로로 자동 fallback하지 않습니다.

스킬 설치 전 기존 파일과 변경분을 비교하고 백업합니다. 소스와 참조 파일을 반영한 뒤 해당 머신에서 만든 `target/release/dot-stk100`을 스킬의 `bin/dot-stk100`으로 설치합니다. 일반 실행 중 자동 설치는 없습니다. `.git`, `target`과 민감한 로컬 자료를 배포하지 않습니다. `bin`은 Git에 저장하지 않으며 Python이나 Rust 소스 파일만 복사한 상태는 native CLI 설치 완료가 아닙니다.

평가기 CLI 식별자와 오류 진단의 의도한 차이는 [마이그레이션 계약](MIGRATION.md)에 기록합니다. 코드 포인트 위치, 원문 CRLF와 finding 순서를 유지합니다. 코드가 바뀌면 release 바이너리도 다시 만들어야 하며 오래된 바이너리로 실행한 검사를 새 소스의 근거로 사용하지 않습니다.

## 고정 Python 기준과 비교

기준 SHA는 `71737d3d10885c77824defb35675405fa5657adb`입니다. 과거 코드는 개발 검증용 별도 archive에만 보존하며 현재 제품 경로에서는 실행하지 않습니다. 기준 archive는 tests/python-baseline-manifest.json의76파일 SHA-256과 먼저 대조합니다.

```bash
# 저장소 밖의 비어 있는 임시 디렉토리를 사용합니다.
baseline_dir=$(mktemp -d)
git archive 71737d3d10885c77824defb35675405fa5657adb | tar -x -C "$baseline_dir"
python3 tests/compare_python.py --baseline "$baseline_dir" --binary target/release/dot-stk100 --capture /tmp/stk-api-results.json
python3 tests/compare_cli.py --baseline "$baseline_dir" --binary target/release/dot-stk100 --output /tmp/stk-cli-results.json
python3 tests/benchmark_cli.py --baseline "$baseline_dir" --binary target/release/dot-stk100 --output /tmp/stk-timings.json
```

API 비교는 정상 결과, Unicode span, 순서, 해시와 직접 정의한 안정적인 오류 진단을 확인합니다. 실제 CLI 비교는 파일 디코딩, 인자 오류, 종료 코드와 renderer의 check/write bytes를 확인합니다. OS/parser가 만드는 오류 문구는 완전한 문자열 동등성 대상에서 제외하되 오류가 stderr에 있고 stdout이 비어 있는지 확인합니다. 명시적인 진단 개선2건은 `intentional_deltas`로 분리합니다.

측정은 1회 예열 후 조건별 최소11회 교대 실행합니다. Python/native/어댑터를 분리하고 모든 회차의 출력 동등성과 해시를 기록합니다. 어떤 회차라도 출력이 다르면 해당 측정은 실패입니다. 실제 호출 빈도, 작업 생산성이나 비용 절감은 이 측정만으로 추정하지 않습니다.

CLI와 파일 검사 통과는 실제 Codex/Claude 모델 호출, 의미 보존 효과와 사람 평가를 증명하지 않습니다.
