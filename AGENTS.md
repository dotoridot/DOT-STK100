# 이 저장소를 수정하는 에이전트의 작업 계약

이 파일은 **프로젝트 개발 지침**이다. 한국어 문서 편집 사용자에게 적용할 스킬은 `SKILL.md`다.

## 우선 읽기

`README.md`, `docs/AGENT-HANDOFF.md`, `docs/IMPLEMENTATION-PLAN.md`, `references/YUPK-STK100-SPEC.md`를 읽는다. 기존 작업 지시·권한 정책을 덮어쓰지 않는다.

## 반드시 지킬 경계

- 이 패키지를 임의의 기존 저장소 루트에 덮어쓰지 않는다. 기존 변경과 경로 충돌을 먼저 확인한다.
- 소유자 승인 없이 원격 push, PR 생성, 이슈 게시, 태그, 릴리스, 공개 상태 변경을 하지 않는다.
- `git reset --hard`, `git clean -fd`, force push, 사용자 변경 삭제를 하지 않는다.
- 사내 자료·비밀·실제 고객 로그·대화 내용을 예제나 테스트에 넣지 않는다. 외부로 전송하지 않는다.
- ASD-STE100·국립국어원 자료의 원문·표·사전을 가져와 라이선스를 바꾸지 않는다.
- 효과를 검증하지 않았으면 효과·정확도·인증을 주장하지 않는다.

## 정본과 변경

규칙 정본은 `rules/rules.json`이다. 규칙 표는 `python scripts/render_rules.py`로 갱신한다. ID를 재사용하지 않는다. SKILL.md·용어집·사례·평가 계획이 상충하는지 함께 검토한다.

규칙을 바꾸면 좋은 예·나쁜 예·모호성·예외와 관련 테스트를 추가한다. 보고 전용 문장 linter는 scripts/lint_text.py다. 패키지 검사기와 의미 검토 엔진을 구분한다. 독립 사람 검토와 호스트 동작 시험은 별도로 기록한다.

## 제출 전 실행

```bash
python scripts/render_rules.py --check
python scripts/validate_package.py
python -m unittest discover -s tests -v
```

검사 명령, 실제 종료 코드, 남은 실패와 미실행 검토를 기록한다. 구조 테스트 통과를 가독성·의미 보존 검증으로 쓰지 않는다.

## 최종 보고

변경한 파일, 실행한 검사, 발견한 문제, 미완료 작업, 원격 변경 여부, 승인 대기 항목을 분리해 보고한다. 결과를 뒷받침할 로그가 없으면 실행 완료라고 쓰지 않는다.
