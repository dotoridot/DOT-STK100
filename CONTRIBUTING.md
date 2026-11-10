# 기여 안내

규칙 제안에는 해결하려는 문제, 원문/교정 예, 반례, 알려진 예외, 출처와 적용 한계를 적는다. 특정 표현을 무조건 금지하는 대신 의미가 바뀌는 조건을 설명한다.

규칙 ID와 본문은 rules/rules.json에서 바꾼다. 생성 표를 손으로 수정하지 않는다. 논문 결과를 인용하면 제목·연도·원문 링크·확인한 범위와 직접 재현 여부를 구분한다.

실제 업무 자료는 공개 권리가 확인된 경우만 제출한다. 회사 코드·고객 로그·비밀·개인정보를 이슈에 올리지 않는다. 재현이 필요하면 독립 가상 예시를 만든다.

사례 기대값에 이견이 있으면 해석·원문 구절·조건 범위를 제시한다. 검토가 끝나기 전에 expected_review를 정답으로 확정하지 않는다. 평가 자료는 원문 계열 단위로 분리한다.

기여할 자료의 공개 권리를 확인하고 이 프로젝트의 MIT 라이선스로 제공할 수 있는 범위에서 제출한다. 제3자 자료의 권리 고지를 보존한다.

## 로컬 검사

```bash
cargo build --release --locked
./target/release/dot-stk100 render --check
./target/release/dot-stk100 validate
python3 -m unittest discover -s tests -v
./target/release/dot-stk100 evaluate
cargo fmt --all -- --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
```

보고 전용 Linter의 경고는 후보로 유지한다. 규칙 변경에는 보존 의도 예, 잘못된 교정, 모호성, 허용 예외를 함께 제출한다. 회귀 데이터는 합성으로 작성하고 label_status를 사람 합의 없이 변경하지 않는다. 저작자 기본 표기는 dotoridot이며 실제 기여자는 합의한 범위에서 별도로 기록한다.

Python 기준과 native의 비교 절차는 [Rust 전환 안내](docs/RUST-MIGRATION.md)를 따른다.
