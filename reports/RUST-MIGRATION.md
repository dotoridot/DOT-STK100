# Rust 전환 검증 기록

작업 ID: DOT-STK100-RUST-20261110. Python 기준은 `71737d3d10885c77824defb35675405fa5657adb`입니다. 이 기록은 코드와 CLI 계약만 다루며 의미 판정, 사람 평가, 실제 모델 문체 효과를 검증하지 않습니다.

| ID | 작업 | 완료 기준 | 상태 |
|---|---|---|---|
| R01 | 기준 동작과 실행 시간 | 고정 입력, 정상/오류 결과, 해시와 측정 조건 보관 | 자료 수집 완료, 독립 검토 대기 |
| R02 | Linter와 평가기 | JSON 값, finding 순서, Unicode span 동등성 | 진행 중 |
| R03 | 규칙표 생성기 | 생성 bytes, check/write, 오류 동등성 | 진행 중 |
| R04 | 패키지 검사기 | 정상/손상 패키지 검출 동등성 | 진행 중 |
| R05 | 소비처, 문서, CI와 리뷰 | native 기본 경로, Python 어댑터, 최신 SHA 리뷰와 필수 검사 | 예정 |
| R06 | 머지 후 설치본 | 기존 차이와 백업, 변경분 반영, 호스트별 release CLI | R05 이후 |

## 기준 자료와 재현

Python 3.15.2, macOS arm64 환경에서 기존 unittest 66개와 생성 표 검사, 패키지 검사를 실행해 통과했습니다. seed 56개, 용어 예시 48개, 표현 예시 24개와 Unicode/CRLF/보호 구간/반복 토큰/오류 설정/패키지 변형을 포함한 742개 API 입력의 기준 결과를 수집했습니다. 이 숫자는 동등성 검사를 위한 합성 입력 수이며 정확도나 독립 표본 수가 아닙니다.

```bash
# 기준 SHA를 별도 임시 디렉토리에 archive한 뒤 실행
python3 tests/compare_python.py --baseline /path/to/python-baseline --capture /path/to/results.json
python3 tests/benchmark_cli.py --baseline /path/to/python-baseline --output /path/to/timings.json
```

측정은 각 CLI의 소형/중형/대형 Linter, seed/용어 평가, 생성 표 check, 패키지 검사 7조건입니다. 한 번 예열하고 조건별 11회 실행합니다. native 구현 후 같은 입력으로 Python/native/어댑터를 교대 실행해 중앙값과 모든 개별 시간을 보관합니다. 전환 전 자료만으로 속도 개선을 주장하지 않습니다.

확인한 import 소비처는 저장소 tests와 두 설치본 tests입니다. 그 밖의 외부 import 사용 여부는 확인할 수 없으므로 기존 Python API는 native 호출 어댑터로 보존합니다. 실행 중 자동 빌드, 다운로드, 외부 모델 호출과 네트워크 전송은 추가하지 않습니다.
