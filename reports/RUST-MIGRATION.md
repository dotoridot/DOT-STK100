# Rust 전환 검증 기록

작업 ID: DOT-STK100-RUST-20261110. Python 기준은 `71737d3d10885c77824defb35675405fa5657adb`입니다. 이 기록은 코드와 CLI 계약만 다루며 의미 판정, 사람 평가, 실제 모델 문체 효과를 검증하지 않습니다.

| ID | 작업 | 완료 기준 | 상태 |
|---|---|---|---|
| R01 | 기준 동작과 실행 시간 | 고정 입력, 정상/오류 결과, 해시와 측정 조건 보관 | 독립 재검토 통과 |
| R02 | Linter와 평가기 | JSON 값, finding 순서, Unicode span 동등성 | 구현과 검증 완료, 지적 대응 재검토 중 |
| R03 | 규칙표 생성기 | 생성 bytes, check/write, 오류 동등성 | 구현과 검증 완료, 지적 대응 재검토 중 |
| R04 | 패키지 검사기 | 정상/손상 패키지 검출 동등성 | 구현과 검증 완료, 지적 대응 재검토 중 |
| R05 | 소비처, 문서, CI와 리뷰 | native 기본 경로, Python 어댑터, 최신 SHA 리뷰와 필수 검사 | 문서와 CI 정리 중 |
| R06 | 머지 후 설치본 | 기존 차이와 백업, 변경분 반영, 호스트별 release CLI | R05 이후 |

## 기준 자료와 재현

Python 3.15.2, macOS arm64 환경에서 기존 unittest 66개와 생성 표 검사, 패키지 검사를 실행해 통과했습니다. seed 56개, 용어 예시 48개, 표현 예시 24개와 Unicode/CRLF/보호 구간/반복 토큰/오류 설정/패키지 변형을 포함한 766개 API 입력의 기준 결과를 수집했습니다. 이 숫자는 동등성 검사를 위한 합성 입력 수이며 정확도나 독립 표본 수가 아닙니다.

```bash
# 기준 SHA를 별도 임시 디렉토리에 archive한 뒤 실행
python3 tests/compare_python.py --baseline /path/to/python-baseline --capture /path/to/results.json
python3 tests/benchmark_cli.py --baseline /path/to/python-baseline --output /path/to/timings.json
```

측정은 각 CLI의 소형/중형/대형 Linter, seed/용어 평가, 생성 표 check, 패키지 검사 7조건입니다. 한 번 예열하고 조건별 11회 실행합니다. native 구현 후 같은 입력으로 Python/native/어댑터를 교대 실행해 중앙값과 모든 개별 시간을 보관합니다. 전환 전 자료만으로 속도 개선을 주장하지 않습니다.

확인한 import 소비처는 저장소 tests와 두 설치본 tests입니다. 그 밖의 외부 import 사용 여부는 확인할 수 없으므로 기존 Python API는 native 호출 어댑터로 보존합니다. 실행 중 자동 빌드, 다운로드, 외부 모델 호출과 네트워크 전송은 추가하지 않습니다.

## 독립 검토와 수정 전 실패

R01의 오류 진단, 실제 CLI 경로, 매 측정 출력 보존 지적을 반영했고 재검토에서 승인됐습니다. 잘못된 진단과 첫 회차 출력 변형, 기준 파일 변조가 이제 검사 실패로 기록됩니다.

R02에서는 잘못된 source 타입을 None으로 바꿔 비교를 생략하는 회귀를 확인했습니다. null/string 외에는 오류를 반환하도록 수정했습니다. 기존 native 실행 파일에서 새 회귀 검사의4개 subtest가 실패한 뒤 수정 후 통과했습니다.

R03/R04에서는 equals 옵션, URL parse/error, nested target/bin 검사 누락과 _native.py 필수 파일 누락을 재현했습니다. 공통 parser, URL 경계 검사와 오류 전파, 루트만 제외하는 재귀 검사, native 필수 파일 목록을 고쳤습니다. package 관련 새 회귀 검사에서 수정 전7개 assertion 실패를 확인하고 수정 후 통과했습니다. 고정 SHA를 별도 archive한 독립 재검토를 진행합니다.

Linter 구현 중 literal backslash 용어 처리와 Python 공백 제어 문자 경계의 실제 불일치도 재현한 뒤 수정했습니다. 기존66개에 native 통합 회귀8개를 더한 Python74개와 Rust13개가 로컬에서 통과했습니다. 이는 해당 검사 범위의 근거이며 임의 Python 정규식 전체, 비표준 JSON, Windows와 실제 모델 동작은 미검증입니다.

API 비교766건 중2건은 malformed label의 TypeError 대신 명시적 진단을 반환하는 의도한 차이이며 `intentional_deltas`에 따로 기록합니다. 나머지 결과와 CLI29조건은 같았습니다. OS/parser 오류 문구는 문자열 동등성 대상에서 제외하고 코드, stderr, 빈 stdout과 파일 bytes를 확인합니다.

## 측정 범위

macOS arm64, Python3.15.2, release 빌드, 조건별1회 예열과11회 교대 실행의 로컬 측정입니다. 모든 실행 결과의 동등성을 함께 확인합니다. 초기에 측정한 native 중앙값은 Python 대비 빠른 조건이 있었지만 Python 어댑터에는 추가 프로세스 비용이 남습니다. 최종 source에서 다시 측정한 값은 제출 전 기록합니다. 실제 작업 시간과 비용 절감을 측정하지 않았습니다.

## 남은 검증

최신 commit의 독립 검토와 CI, 원격 PR 스레드 정리와 머지, 기존 설치본 차이/백업 확인과 승인된 변경분 반영은 아직 완료로 표시하지 않습니다. 설치본 파일과 CLI, 실제 모델 호출과 의미 보존 효과를 구분해 보고합니다.
