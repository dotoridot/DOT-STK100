# Codex와 Claude Code 설치 및 호환성 상태

확인일: 2026-11-08. 형식 근거는 [Agent Skills 명세](https://agentskills.io/specification), Codex 위치와 호출은 [OpenAI 공식 문서](https://learn.chatgpt.com/docs/build-skills), Claude Code 위치와 호출은 [Anthropic 공식 문서](https://code.claude.com/docs/en/skills)다.

| 호스트 | 프로젝트 범위 | 사용자 범위 | 명시적 호출 |
|---|---|---|---|
| Codex | `.agents/skills/dot-stk100/SKILL.md` | `~/.agents/skills/dot-stk100/SKILL.md` | `$dot-stk100` |
| Claude Code | `.claude/skills/dot-stk100/SKILL.md` | `~/.claude/skills/dot-stk100/SKILL.md` | `/dot-stk100` |

배포 승인 전에는 이 로컬 패키지를 직접 복사해 사용할 수 있다. SKILL.md만 복사하지 않는다. 전체 패키지 복사 시 .git, __pycache__, .venv, .env, private, local-runs와 기존 설치 폴더를 제외한다. 이미 동명 스킬이 있으면 덮어쓰지 말고 비교한 뒤 교체한다. 이 작업에서 실제 사용자 설치 폴더를 변경하지 않았다.

SKILL 진입 파일은 공통 보존 원칙과 프로필/모드 선택을 담당한다. Lite는 lite.md, Core는 core.md, Audit은 audit.md와 rules.json을 읽도록 지시한다. 용어/근거/상세 규격은 필요한 경우에만 추가한다. 파일 크기나 로딩 지시의 존재만으로 실제 모델의 토큰 절감률과 행동 준수를 주장하지 않는다.

## 검증 행렬

| 항목 | 실행 상태 | 증명하지 못하는 것 |
|---|---|---|
| Agent Skills 필수 필드와 상대 파일 링크 | 패키지 검사에서 확인 | YAML/CFF 전체 표준 적합성 |
| 두 프로젝트 설치 레이아웃의 임시 복사본 | 로컬 구조 시험 | 호스트의 자동 발견과 모델 출력 |
| Codex/Claude 명령의 버전 조회 | 조회 결과만 실행 로그 기록 | 스킬 로딩이나 의미 보존 |
| 각 호스트에서 Lite/Core/Audit 호출 | 미실행 | 실제 행동 호환성 |
| 악성 인용 지시를 가진 모델 입력 | 미실행 | 지시 주입 저항성 |
| 실제 호스트의 네트워크 정책/데이터 전송 | 미실행 | 외부 전송의 기술적 차단 |
| Linter의 보호 구간과 파일 보존 | 합성 로컬 회귀 테스트 | 전체 Markdown과 의미 정확성 |

## 후속 호스트 실행 절차

각 호스트의 격리된 프로젝트에 합성 자료만 복사한다. 다른 개인 스킬이 개입하지 않는지 기록한다. 정상 설명, 조건 교정, 숫자 변경 검토, 근거 부족 검증, 파일 읽기 실패, 인용 속 명령을 프로필별로 요청한다. 실제 읽은 파일, 도구 호출과 출력, 호스트/모델 버전, 사람 확인을 기록한다.

예: Audit review에 examples/source.md와 examples/candidate.md를 제공하면 숫자 3회/5회의 차이와 조건 범위 위험을 구절로 보고해야 한다. 원문에 없는 주체를 채우거나 Linter 경고를 의미 변경 확정으로 인용하면 실패 후보로 기록한다. 실제 실행 전까지 이 기대 동작을 통과 결과로 표시하지 않는다.

실제 버전 조회: codex-cli 0.167.0, Claude Code 2.1.319. 두 명령 모두 --version만 실행했다. 임시 레이아웃 기록: [host-layout-output.txt](../reports/pre-rebrand/host-layout-output.txt).

위 임시 레이아웃 기록은 이름 변경 전 작업의 기록이다. 현재 이름의 실제 호스트 호출 시험은 수행하지 않았다.

## Rust 실행 파일의 설치 경계

Rust 전환 후에는 [빌드 안내](RUST-MIGRATION.md)에 따라 각 실행 머신에서 release 실행 파일을 만들어 `bin/dot-stk100`에 둡니다. 호스트 모델을 호출하는 것과 설치 파일 검사, native CLI 실행을 별도로 기록합니다. 위 표의 과거 미실행 항목을 Rust 코드 검사만으로 완료 처리하지 않습니다.
