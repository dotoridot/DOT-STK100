# 실제 검사 기록

실행일: 2026-11-08. 대상: YSK-STK100 0.2.0-draft.2. 저작자: youngssangkwon.

## 환경과 입력

이번 실행 환경은 macOS(Darwin), x86_64, Python 3.13.0이다. 입력 ZIP의 35개 파일이 제공된 해제 폴더와 동일함을 수정 전에 확인했다. 입력 ZIP은 변경하지 않았다. 원 패키지의 Linux/Python 3.13.5 검사 기록은 [input-draft1/VALIDATION.md](input-draft1/VALIDATION.md)에 보존했다. 원 기록의 실행을 이번 환경에서 한 것처럼 주장하지 않는다.

## 최종 명령과 결과

| 명령/검사 | 실제 결과 | 확인 범위 |
|---|---|---|
| python3 scripts/render_rules.py --check | 종료 코드 0 | 정본 32개 규칙과 생성 표 동기화 |
| python3 scripts/validate_package.py | 종료 코드 0 | 파일, JSON, 제한적 메타데이터, 상대 링크와 참조 |
| python3 -m unittest discover -s tests -v | 종료 코드 0, 49개 통과 | 구조 24개, Linter 23개, 개발 집계 2개 회귀 테스트 |
| python3 scripts/evaluate_linter.py | 종료 코드 0 | 합성 56건/28계열의 AI 초안 라벨 대비 경고 발생 집계 |
| python3 scripts/lint_text.py --source examples/source.md --candidate examples/candidate.md --format json | 종료 코드 0, 후보 경고 보고 | 보고 형식과 실행 예. 파일 미수정은 회귀 테스트에서 별도 확인 |
| 두 호스트 설치 레이아웃 임시 복사 검사 | 각 종료 코드 0 | 전체 패키지 상대 참조. 실제 호스트 실행 아님 |
| Ruby 표준 YAML 파서 | 종료 코드 0 | SKILL front matter와 CITATION YAML 구문 및 지정 저작자 확인. CFF 전체 스키마 아님 |
| skill-creator quick_validate.py | 종료 코드 1 | 환경에 PyYAML이 없어 실행 불가. 통과로 계산하지 않음 |

실제 출력과 종료 코드는 [validation-output.txt](validation-output.txt), [host-layout-output.txt](host-layout-output.txt)에 있다. 버전 조회 결과는 codex-cli 0.167.0, Claude Code 2.1.319이며 --version만 실행했다. 의존성 설치나 전역 스킬 설정 변경은 하지 않았다.

## 개발 경고 집계

[LINTER-EVALUATION.json](LINTER-EVALUATION.json)의 잠정 집계: TP 20, FP 11, TN 15, FN 6, needs_context 제외 4건. 단위는 수정문 1건의 경고 유무다. 관련 없는 경고도 양성으로 세므로 이 결과는 의미 판정 성능이 아니다. 라벨은 AI 초안이며 사람 precision/recall은 null이다. 같은 pair_id는 독립 표본이 아니다.

실제 오탐/미탐 반례에는 안전한 문장 분리와 숫자 압축 경고, 주체-값 연결 또는 조사의 의미 변화 미탐이 포함된다. 분모와 사례 ID를 함께 남겼다. 개발 자료에 맞춘 집계를 독립 잠금 평가나 일반 정확도로 광고하지 않는다.

## 검사하지 않은 것

독립 사람의 의미 주석/합의, 규격의 기술적 정확성, 사실의 참·거짓, 한국어 분야별 효과, 독자 이해도/실행 과제, 실제 Codex/Claude 스킬 호출, 모델의 파일 읽기/지시 주입 저항/네트워크 통제, 모든 OS/Python 버전, 공식 CFF/JSON Schema 전체 적합성, 상표 권리와 최종 공개 라이선스 채택은 검증하지 않았다.

패키지 검사기는 전체 Markdown/YAML/CFF 검증기가 아니다. Linter는 보호 구간 일부와 문자열 휴리스틱만 다루고 모든 경고를 WARN/candidate로 남긴다. 49개 테스트 통과로 규격의 의미 보존 성능을 입증했다고 주장하지 않는다.

## 배포 상태

원격 저장소 생성/설정, Git 커밋, Push, PR, 공개, 태그, 릴리스를 수행하지 않았다. 라이선스와 원격 배포 승인은 남아 있다. 배포용 ZIP의 재추출 구조 검사는 [archive-check.txt](archive-check.txt)에 기록한다. 로컬 압축본은 공개 릴리스가 아니다.
