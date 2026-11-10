# 로컬 보고 전용 Linter

Rust로 구현한 로컬 휴리스틱 검사기다. 실행 파일은 명시적으로 release 빌드하며 [빌드와 호환 경로](RUST-MIGRATION.md)를 따른다. 자동 수정, 파일 저장, 네트워크 요청, 모델 호출과 의미 적합 판정을 하지 않는다. stdout에 JSON을 쓰고 오류는 stderr에 기록한다. JSON에는 입력 구절이 포함되므로 민감한 문서의 결과도 로컬에 보관한다.

```bash
./target/release/dot-stk100 lint --source examples/source.md --candidate examples/candidate.md --format json
./target/release/dot-stk100 lint --candidate examples/candidate.md
./target/release/dot-stk100 evaluate
./target/release/dot-stk100 evaluate --terminology-examples
```

원문이 없으면 주체/지시 대상과 표기 혼용 후보만 검사하고 나머지는 checks_skipped에 기록한다. 종료 코드 0은 요청한 검사 실행 완료, 2는 입력/설정/실행 오류다. 위반 게이트와 종료 코드 1은 구현하지 않았다. 경고 유무로 의미 보존을 판정하지 않는다.

| 검사 | 현재 구현 | 알려진 오탐 또는 미탐 |
|---|---|---|
| 용어 | 표기 혼용, 구별 개념의 사용량 교차 변화, 권장 표현 신호 | 같은 개념인지 확정 못함. 용어 변경 아닌 삭제/추가도 경고 가능 |
| 주체 | 일부 지시 표현과 피동 표현 후보 | 정상 피동문도 경고. 주체 추측과 생략 전반을 분석하지 못함 |
| 조건 | 조건/예외 표지 변화, 조건이 있는 글의 문장/목록 경계 수 변화 | 안전한 분리도 경고. 경계 수가 같아도 범위가 바뀔 수 있음 |
| 값 | 십진수, 버전, 일부 단위, 비교 표지의 순서/개수/표기 비교 | 각각 같은 값의 압축, 문장 순서 교환도 경고. 대상만 바뀌면 미탐 가능. 모든 수식/지수/16진수 해석은 미지원 |
| API/식별자 | 코드 보호 구간, 일부 영문 대문자/underscore/camelCase/호출 표기 | 일반 영단어와 임의 언어 식별자는 놓칠 수 있음 |
| 부정 | 일부 한국어 부정 어휘 변화 | 같은 부정의 활용 변화도 경고. 논리적 부정 범위와 완전한 동의 표현은 미분석 |
| 불확실성 | 가능성, 추정, 예정, 계획 등의 표지 변화 | 계획/예정 교체도 경고. 간접적인 불확실성 표현은 미탐 가능 |

탐지와 차단은 동의어가 아니다. references/terminology.json은 의미 구별 목록이다. 표기 혼용 설정은 별도 references/lint-terms.json으로 분리하며 `--terms project-terms.json`으로 대체할 수 있다. 표준 용어를 자동 강제하지 않는다.

## 보호 구간과 위치

backtick/tilde fence, 같은 길이 backtick의 인라인 코드, 일부 인용, Markdown 링크 목적지/URL, 들여쓰기 코드, `>` 인용/`|` 표/INFO·WARN·ERROR·DEBUG 로그 줄을 보수적으로 비교한다. 해당 구간은 일반 문장 휴리스틱에서 제외한다. 인용 속 명령은 실행하지 않는다.

완전한 CommonMark 분석기가 아니다. 중첩 HTML, 모든 표 형식, reference-style 링크, 모든 인용 방식과 로그 형식을 인식하지 못한다. 보호 구간의 재배치나 표 문구 교정도 경고할 수 있다. 닫히지 않은 fence는 나머지를 보호하지만 문서 구문 오류를 확정하지 않는다. 코드 내용이 같은데 주위 산문의 역할만 바뀌는 위험도 놓칠 수 있다.

span은 원본 Python Unicode 코드 포인트 기준 0-based, 끝 제외다. line/column은 1-based다. UTF-8 바이트나 UTF-16 코드 단위가 아니다. Unicode 정규화와 CRLF 변환을 하지 않는다. 제거/추가는 반대편 span이 null일 수 있다. 원문 전체를 연결해 출력하지 않지만 발견 구절은 JSON에 들어간다.

모든 finding의 certainty는 candidate, severity는 WARN이다. confirmed와 의미 verdict는 생성하지 않는다. checks_skipped에는 사실/인과/주체 연결/사람 검토 등 미지원 범위를 항상 기록한다.

## 의미 구분 사전과 개발 예시

`references/terminology.json`의 16개 용어 쌍에는 규칙 ID, 정의, 예시와 예외가 있다. 구별 개념의 사용량이 교차해 바뀌면 기존 `terminology` 경고의 message에 `TERM-*` ID를 포함한다. JSON 출력 스키마와 `--terms`의 표기 혼용 설정 계약은 유지한다. `--terms`는 의미 구분 사전을 대체하는 옵션이 아니다.

이 검사는 단어 부분 문자열의 개수를 비교한다. 프로젝트 정의와 예외를 자동 해석하지 않으며 용어 사용량이 같게 남은 역할 교환은 놓칠 수 있다. 경고가 의미 변경 확정은 아니고, 경고가 없다고 보존을 확인한 것도 아니다.

`--terminology-examples`는 사전에 포함된 개발 예시 48건을 기존 집계 경로로 실행한다. 기본 seed 자료 56건과 별도 입력이다. `--cases`와 동시에 사용할 수 없다. 단위는 문서 하나에서 아무 경고나 발생했는지이며 `needs_context` 16건은 이진 지표에서 제외한다. 기대 라벨이 AI 초안이므로 사람 기준 precision과 recall은 null이다.

## 권장 표현 후보와 출력 버전

`references/preferred-expressions.json`의 8개 항목에서 고정 문자열 신호를 읽어 후보 문서의 편집 지점을 알린다. 기존 `terminology` check 안에서 `rule_id: YSK-K07`과 `EXPR-*` ID를 사용하므로 의미 구분의 K05/TERM 경고와 구분할 수 있다. 예를 들어 초기화를 수행이라는 표현은 초기화하다라는 후보와 적용 조건 확인 안내를 낸다.

경고는 원문이 없거나 원문과 후보가 같아도 발생할 수 있다. 반대로 수정문이 직접적인 동사를 사용하면 원문의 신호가 사라져 후보 경고가 없을 수 있다. 경고 유무를 위반 여부나 의미 보존으로 해석하지 않는다.

일부 Markdown 보호 구간을 제외하고 문자열 접두부를 찾으며, 완전한 한국어 형태소 분석은 하지 않는다. 부정형에서도 후보를 알릴 수 있으므로 부정과 의무 수준을 사람이 대조해야 한다. 프로젝트의 고유 용어를 일반 본문에 썼을 때 자동 예외 처리하지 않는다. signals는 정규식이 아닌 고정 문자열이고 자동 교정값은 제공하지 않는다.

출력 schema_version은 0.2, tool_version은 0.2.0이다. config_hashes.expressions를 추가해 권장 표현 사전의 SHA-256을 기록한다. 출력 스키마를 고정해 검증하는 소비자는 eval/lint-output.schema.json 0.2를 사용해야 한다. 단일 문서 any-warning 집계에는 문체 후보도 포함되므로 과거 수치와 의미 검사 성능으로 비교하지 않는다.
