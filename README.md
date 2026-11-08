# YUPK-STK100

**YUPK Simplified Technical Korean — 기술적 의미를 지키며 한국어 설명을 명확하게 쓰는 규격.**

저작자: **dotoridot** · 기획·프로젝트 관리: **dotoridot** · 버전: `0.2.0-draft.3` · 상태: 연구 기반 설계 초안, 효과 검증 전

문장을 짧게 만드는 것보다 **조건·부정·수치·주체·예외·근거 수준을 보존하는 것**을 우선합니다. SDK/API 문서, 코드 리뷰, 장애 분석, 운영 절차, AI 기술 설명에 사용합니다.

이 프로젝트는 ASD·STEMG와 관계없는 독립 프로젝트입니다. 공식 한국어판·공인 표준·인증 도구가 아닙니다. `100`은 이름의 일부이며 규칙 수나 품질 점수가 아닙니다.

## 바로 사용할 프롬프트

```text
첨부한 YUPK-STK100 규격과 SKILL.md를 읽고 rewrite 모드로 편집하세요.
기술적 주장·조건·부정·수치·단위·식별자·예외·불확실성을 보존하세요.
원문의 오류나 모호성은 별도로 표시하고, 사실을 몰래 바꾸지 마세요.
문장 길이 때문에 정보를 삭제하지 마세요. 원문에 없는 주체도 추가하지 마세요.
결과는 수정문, 중요한 변경, 확인 필요 사항으로 나누어 제시하세요.
```

프로젝트 이름만 쓰면 모델이 규칙을 알고 있다고 보장할 수 없습니다. 규격을 함께 제공하거나 실제로 읽을 수 있는 스킬로 설치해야 합니다.

## 구성

| 파일 | 용도 |
|---|---|
| [규격](references/YUPK-STK100-SPEC.md) | 32개 독립 규칙, 작업 모드, 한국어 의미 보존 기준 |
| [SKILL.md](SKILL.md) | 설명·교정·검토·검증을 수행하는 에이전트 지시 |
| [연구 검토](references/RESEARCH.md) | 원문 근거, 확인 범위, 적용 한계 |
| [에이전트 작업 지시서](docs/AGENT-HANDOFF.md) | 저장소 추가와 후속 구현 시작점 |
| [작업 계획](docs/IMPLEMENTATION-PLAN.md) | 우선순위·의존성·완료 기준 |
| [평가 계획](docs/EVALUATION.md) | 의미 보존·이해도·오탐을 분리하는 실험 |
| [기존 스킬 연계](docs/INTEGRATION.md) | korean-humanizer와 역할 분리 |
| [사례](examples/BEFORE-AFTER.md) | 가상 교정 예와 잘못된 단순화 |
| [공개 체크리스트](docs/RELEASE-CHECKLIST.md) | 저작자·권리·보안·검증·승인 |

## 제공되는 것과 제공되지 않는 것

제공: 규격, Lite/Core/Audit 스킬 경로, 용어 구분 사전, 합성 회귀 사례, 로컬 보고 전용 Linter, 오탐/미탐 집계 도구, 사람 검토 대기 자료, 패키지 구조 검사기.

미제공: 의미 동치 증명기, 학습 모델, 사람 대상 효과 검증, 실제 호스트별 설치 테스트, 원격 저장소 배포.

## 설치와 사용

이 폴더는 독립 저장소로 공개하기 위한 로컬 작업본입니다. 공개 저장소는 https://github.com/dotoridot/YUPK-STK100 입니다. 다운로드하거나 복사한 전체 폴더를 아래 위치에 두며, 기존 동명 폴더가 있으면 덮어쓰지 말고 먼저 비교하세요.

| 호스트 | 프로젝트 설치 | 개인 설치 |
|---|---|---|
| Codex | `.agents/skills/yupk-stk100/` | `~/.agents/skills/yupk-stk100/` |
| Claude Code | `.claude/skills/yupk-stk100/` | `~/.claude/skills/yupk-stk100/` |

프로젝트 범위 설치 예시입니다. 기존 동명 폴더가 있으면 먼저 비교하세요.

```bash
# Codex 프로젝트 설치
git clone https://github.com/dotoridot/YUPK-STK100.git .agents/skills/yupk-stk100

# Claude Code 프로젝트 설치
git clone https://github.com/dotoridot/YUPK-STK100.git .claude/skills/yupk-stk100
```

SKILL.md만 떼어 복사하면 참조가 깨집니다. 전체 패키지를 복사하고 캐시, .git, private, local-runs는 제외하세요. 설치 위치의 원본을 확인한 뒤 Codex는 `$yupk-stk100`, Claude Code는 `/yupk-stk100`으로 호출합니다. 경로와 형식은 공식 문서에서 확인했지만 실제 두 호스트의 모델 실행은 미검증입니다. [설치 근거와 시험 상태](docs/HOST-COMPATIBILITY.md)를 참고하세요.

```text
$yupk-stk100 Lite explain: 요청 타임아웃과 사용자의 취소는 어떻게 다른가요?
/yupk-stk100 Core rewrite: 아래 합성 API 설명을 원문의 조건과 수치를 유지해 고쳐 주세요.
$yupk-stk100 Audit review: 아래 원문과 수정문의 의미 변경 위험을 검토해 주세요.
```

단독 AI 대화에서는 Lite/Core/Audit과 explain/rewrite/review/verify를 지정하고 해당 스킬 파일을 읽도록 요청합니다. 프로필은 검토 깊이, 모드는 작업 종류입니다.

## 보고 전용 Linter

```bash
python3 scripts/lint_text.py --source examples/source.md --candidate examples/candidate.md --format json
```

결과는 수정 없이 stdout JSON으로 보고합니다. 모든 경고는 후보입니다. 종료 코드 0이나 경고 없음은 의미 보존 합격이 아닙니다. [검출 범위, 위치 규약, 오탐과 미탐](docs/LINTER.md)을 확인하세요.

## 로컬 구조 검사

Python 3.11 이상을 이 패키지의 지원 목표로 정했습니다. 런타임 외 추가 의존성·네트워크 연결은 필요하지 않습니다.

```bash
python scripts/render_rules.py --check
python scripts/validate_package.py
python -m unittest discover -s tests -v
python scripts/evaluate_linter.py
```

이 명령은 파일 구조·참조·테스트 자료 형식을 검사합니다. 문장의 의미와 사실을 검증하는 명령이 아닙니다. 실행 기록은 [검사 보고서](reports/VALIDATION.md)에 있습니다.

## 저작자와 라이선스

인용 이름은 **dotoridot**입니다. [AUTHORS.md](AUTHORS.md)와 [CITATION.cff](CITATION.cff)에 프로젝트 저작자 표기를 준비했습니다.

문서, 규칙, Skill, 합성 자료, 실행 코드와 테스트를 모두 [MIT 라이선스](LICENSE)로 제공합니다. 저작권 고지의 저작자는 dotoridot입니다. 외부 표준과 논문 등 제3자 자료의 권리는 각 권리자에게 있으며 원문을 묶어 배포하지 않습니다.

## 검토 결과와 기여

[초안 감사와 단계별 상태](reports/AUDIT.md), [실행 기록](reports/VALIDATION.md), [개발 자료 경고 집계](reports/LINTER-EVALUATION.json), [기여 안내](CONTRIBUTING.md), [변경 이력](CHANGELOG.md)을 제공합니다. 독립 사람 검토, 효과 평가, 저장소 생성과 공개 배포는 아직 완료되지 않았습니다.
