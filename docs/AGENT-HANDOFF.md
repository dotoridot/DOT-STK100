# 후속 에이전트 작업 인계

프로젝트: DOT-STK100. 정식 명칭: DOT Simplified Technical Korean. 저작자: dotoridot. 기획·관리: dotoridot. 작업책임자: 사용자(CWO).

현재 사용자 지시는 P0-P3의 로컬 개선이다. 이전 패키지의 P0만 수행하라는 안내는 이번 지시로 대체됐다. 사용자는 계정 이전에 따른 기존 저장소 수정과 DOT-STK100 공개 저장소 생성/업로드를 승인했다. 태그/릴리스와 별도 서비스 게시까지 자동 확대하지 않는다.

## 먼저 확인

README.md, AGENTS.md, reports/AUDIT.md, reports/VALIDATION.md와 docs/IMPLEMENTATION-PLAN.md를 읽는다. rules/rules.json이 규칙 정본이며 표는 `dot-stk100 render`로 생성한다(기존 Python 경로는 호환 어댑터). 입력 ZIP은 원본으로 유지했다. 제공 폴더가 ZIP 35개 파일과 일치함을 확인한 뒤 기존 해제본을 수정했다. 로컬 검토 폴더는 git init 하지 않았다. 원격 dotoridot/DOT-STK100은 생성해 공개 초안을 반영했다.

## 이번 로컬 구현

보고 전용 Linter는 scripts/lint_text.py, 개발 자료 경고 집계는 scripts/evaluate_linter.py다. 전체 문장 의미를 판정하지 않는다. Lite/Core/Audit은 필요한 참조만 읽는다. 사용자 본문을 외부 모델이나 검색으로 전송하지 않는다.

## 남은 검토

- P0: 프로젝트 전체 MIT 적용은 사용자가 선택했다. 실제 원격 공개와 그 결과를 별도로 확인한다.
- P2: 독립 사람 2명의 의미 주석과 제3자 합의, 경고의 타당성 주석, 잠금 평가와 독자 과제는 미실행이다.
- P3: 실제 Codex/Claude Code 모델 실행과 파일 읽기/지시 주입/외부 통신 검토는 미실행이다. 임시 설치 구조 시험과 실제 호스트 실행을 구분한다.
- ASD 공식 원문은 이번에 직접 열기 실패했다. 기존 패키지의 권리 안내 열람 주장이나 미검증 한국어 효과를 확인 완료로 바꾸지 않는다.

## 제출 전 검사

```bash
cargo build --release --locked
./target/release/dot-stk100 render --check
./target/release/dot-stk100 validate
python3 -m unittest discover -s tests -v
./target/release/dot-stk100 evaluate
```

명령과 실제 종료 코드를 기록한다. 구조·회귀·AI 라벨 경고 집계·사람 검토를 분리한다. 저장소 생성, Push, PR, 태그, 릴리스, 공개 상태 변경은 별도 승인 전 수행하지 않는다.

Rust 전환은 [전환 안내](RUST-MIGRATION.md)와 [검증 기록](../reports/RUST-MIGRATION.md)을 따른다. native 빌드, Python 어댑터, 실제 호스트 모델 실행을 별도로 보고한다.
