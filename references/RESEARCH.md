# 연구 검토와 설계 근거

검토일: 2026-11-08. 대상: 0.2.0-draft.3. 목적 지향 1차 자료 검토이며 체계적 문헌 고찰이나 메타분석이 아니다.

DOT-STK100의 기술적 정확성, 의미 보존 성능과 독자 이해도 향상은 아직 검증하지 않았다. 출처의 결과와 프로젝트의 설계 가설을 구분한다. 외부 원문 규칙, 사전, 표, 데이터셋은 복제하지 않았다.

정본 기록은 [sources.json](sources.json)이다. checked_this_run은 표시한 범위의 열람만 뜻한다. HTTP 403과 원 패키지의 미재확인 주장도 기록한다.

## R01. ASD-STE100 Simplified Technical English, Issue 9

저자: ASD / STEMG. 발행: 2025-01 (official FAQ index; exact day not reverified). [원문](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).

확인 상태: partial_index_only_direct_fetch_blocked. 공식 FAQ 검색 색인에서 Issue 9와 2025년 1월 배포, 규칙/사전 구성을 확인했다. 공식 소개와 PDF 직접 열기는 HTTP 403으로 실패했다. 원문 표지·권리 안내를 이번에 읽었다고 주장하지 않는다.

적용할 원칙: 규칙과 용어를 함께 관리하되 독립적인 한국어 규칙을 설계한다.

적용 한계: 통제 언어의 규칙·용어 관리 접근을 참고. 공식 한국어판 또는 인증이라고 주장하지 않음.

실험 가설: 한국어에서 조건 범위 보존을 별도 검사하면 오해가 줄어드는가?

## R02. A Survey and Classification of Controlled Natural Languages

저자: Tobias Kuhn. 발행: 2014. [원문](https://aclanthology.org/J14-1005/).

확인 상태: checked_this_run. ACL 저자·서지와 논문 PDF 도입부의 CNL 목적/분류를 확인했다. 전문 전체 정독과 실험 재현 없음.

적용할 원칙: 통제 언어의 목적과 적용 범위를 먼저 정의한다.

적용 한계: 통제 언어를 목적에 맞게 설계하는 근거. YSK 규칙의 효과를 검증한 자료는 아님.

실험 가설: 일반 간결화 대비 목적별 규칙의 오류 감소 효과가 있는가?

## R03. 한눈에 알아보는 공공언어 바로 쓰기(개정판)

저자: 국립국어원. 발행: 2022-12-26. [원문](https://m.korean.go.kr/front/etcData/etcDataView.do?etc_seq=699&mn_id=46&pageIndex=1).

확인 상태: checked_this_run. 공식 게시일과 PDF 공공언어 요건 항목(인쇄 9쪽, PDF index 9)을 확인했다. 권리 유형 표시는 이번 열람에서 재확인하지 못했다.

적용할 원칙: 정확성과 소통성을 별도 검토한다.

적용 한계: 정확성과 소통성을 구분해 평가하는 설계 참고. 기술 문서용 어절 임계값을 제공하는 근거로 사용하지 않음.

실험 가설: 주체 생략과 조사 변경의 위험을 검토자가 일관되게 주석할 수 있는가?

## R04. Optimizing Statistical Machine Translation for Text Simplification

저자: Wei Xu; Courtney Napoles; Ellie Pavlick; Quanze Chen; Chris Callison-Burch. 발행: 2016. [원문](https://aclanthology.org/Q16-1029/).

확인 상태: checked_this_run. ACL 서지·초록과 PDF SARI 설명/평가 논의 일부를 확인했다. 전체 논문 정독과 재현 없음.

적용할 원칙: 추가·유지·삭제를 구분하되 의미 판정을 별도로 둔다.

적용 한계: 추가·유지·삭제 평가의 참고. 한국어 기술 문서의 의미 보존 인증 지표로 사용하지 않음.

실험 가설: 한국어 토큰화에 따른 지표 변동은 어느 정도인가?

## R05. LENS: A Learnable Evaluation Metric for Text Simplification

저자: Mounica Maddela; Yao Dou; David Heineman; Wei Xu. 발행: 2023. [원문](https://aclanthology.org/2023.acl-long.905/).

확인 상태: checked_this_run. ACL 서지·초록의 SimpEval과 LENS 제안을 확인했다. 모델 및 실험 미실행.

적용할 원칙: 자동 점수를 사람 판단과 별도로 대조한다.

적용 한계: 사람 판단과의 평가 정합성을 점검해야 한다는 참고. 이 모델을 검증 없이 한국어 심사기로 채택하지 않음.

실험 가설: 한국어 기술 문서에서 사람 의미 판정과 어떤 관계가 있는가?

## R06. Dancing Between Success and Failure: Edit-level Simplification Evaluation using SALSA

저자: David Heineman; Yao Dou; Mounica Maddela; Wei Xu. 발행: 2023. [원문](https://aclanthology.org/2023.emnlp-main.211/).

확인 상태: checked_this_run. ACL 서지·초록에서 편집 단위 사람 주석 체계를 확인했다. 원 패키지의 PDF 3482쪽/Table 4 열람 주장은 이번에 재확인하지 않았다.

적용할 원칙: 주장과 편집 단위의 손실·추가를 기록한다.

적용 한계: 문장 전체 점수 외에 편집 단위의 성공·오류를 기록. 원래 분류체계 전체를 복제하지 않음.

실험 가설: 한국어 편집 유형의 평가자 일치도는 충분한가?

## R07. Right at My Level: A Unified Multilingual Framework for Proficiency-Aware Text Simplification

저자: Jinhong Jeong; Junghun Park; Youngjae Yu. 발행: 2026-07. [원문](https://aclanthology.org/2026.acl-long.1086/).

확인 상태: checked_this_run. ACL 서지·초록에서 한국어를 포함한 L2 숙련도별 단순화와 Re-RIGHT 제안을 확인했다. 원 패키지의 Limitations 쪽수 열람은 이번에 재확인하지 않았다.

적용할 원칙: 독자 수준을 지정하고 기술 식별자 보존을 따로 평가한다.

적용 한계: 한국어 포함 숙련도별 어휘 조절 연구. 제2언어 학습의 어휘 난도 결과를 보안 문서 정확성으로 일반화하지 않음.

실험 가설: 숙련도별 쉬운 어휘가 기술 독자 이해에 도움이 되는가?

## R08. Agent Skills Specification

저자: Agent Skills maintainers. 발행: living_document. [원문](https://agentskills.io/specification).

확인 상태: checked_this_run. 공식 Agent Skills 명세의 SKILL.md 필수 name/description, metadata와 지원 폴더 구성을 확인했다.

적용할 원칙: 공통 파일 형식과 필요한 참조만 로딩하는 구조를 따른다.

적용 한계: 스킬 패키징만 참고. 모든 에이전트의 설치·호환·권한 차단을 보장하지 않음.

실험 가설: 호스트별 실제 로딩과 상대 참조가 일치하는가?

## R09. Creative Commons Attribution 4.0 International: Legal Code

저자: Creative Commons. 발행: 2013 (CC BY 4.0 version; legal text retrieved 2026-11-08). [원문](https://creativecommons.org/licenses/by/4.0/legalcode.en).

확인 상태: checked_this_run. 공식 CC BY 4.0 법률 문서의 공개 라이선스 구조와 표시 조건을 확인했다. 프로젝트 소유자의 채택 승인은 받지 않았다.

적용할 원칙: 문서 재사용의 권리/출처 범위를 표시한다.

적용 한계: 문서 라이선스 제안. 이름의 상표 등록·독점권 또는 모든 생성 결과의 저작자 표시 의무를 뜻하지 않음.

실험 가설: 선택한 라이선스 범위를 기여자가 오해 없이 구분하는가?

## R10. The MIT License

저자: Open Source Initiative. 발행: living_document. [원문](https://opensource.org/license/mit).

확인 상태: checked_this_run. OSI의 MIT 공식 본문을 확인했다. 프로젝트 코드의 공개 채택 승인은 별도다.

적용할 원칙: 도구 코드의 권리자 고지를 일관되게 준비한다.

적용 한계: 실행 도구 라이선스 제안. 저작권자 승인 전 공개 배포를 대신하지 않음.

실험 가설: 코드/문서의 분리 라이선스 안내가 충분한가?

## R11. About CITATION files

저자: GitHub Docs. 발행: living_document. [원문](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files).

확인 상태: inherited_not_reverified. 원 패키지에 들어 있던 GitHub 인용 파일 안내 기록이다. 이번 작업에서는 공식 페이지를 재확인하지 않았다.

적용할 원칙: 확인하지 않은 DOI나 저장소 URL을 만들지 않는다.

적용 한계: 작성자 인용 메타데이터 제공. DOI나 학술 검증 실적을 만들지 않음.

실험 가설: 실제 공개 후 CFF 표시가 의도대로 노출되는가?

## G01. korean-humanizer / SKILL.md and LICENSE

저자: dotoricode. 발행: snapshot_2026-11-08. [원문](https://github.com/dotoridot/korean-humanizer/blob/main/SKILL.md).

확인 상태: inherited_not_reverified. 원 패키지의 연결 GitHub 열람 주장이다. 이번 작업에서는 저장소나 라이선스를 재확인하지 않았다.

적용할 원칙: 다른 스킬의 계약을 무단으로 바꾸지 않는다.

적용 한계: 기술 문서를 제외하는 현재 계약을 보존. 자동 후처리 체인 대신 명시적 용도별 라우팅을 제안.

실험 가설: 별도 승인 후 혼합 문서 라우팅을 실제 시험할 수 있는가?

## R12. 전자 제품 사용 설명서 텍스트 분석 - 테크니컬 라이팅(Technical Writing)의 실제 -

저자: 남경완 (Nam Kyoung-Woan). 발행: 2018. [원문](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002382879).

확인 상태: checked_this_run. KCI의 저자·발행 연도·국문/영문 초록을 확인했다. 논문 전문은 확인하지 않았다.

적용할 원칙: 용어 일관성, 문장 의미 연결, 예측 가능한 정보 배열을 설계 참고로 삼는다.

적용 한계: 전자 제품 설명서 분석을 SDK·보안 문서 효과 검증으로 일반화하지 않는다.

실험 가설: 조사·조건 연결의 명시적 검토가 기술 문서의 의미 손실을 줄이는가?

## R13. Evaluating Document Simplification: On the Importance of Separately Assessing Simplicity and Meaning Preservation

저자: Liam Cripwell; Joël Legrand; Claire Gardent. 발행: 2024. [원문](https://aclanthology.org/2024.readi-1.1/).

확인 상태: checked_this_run. ACL 서지·초록, PDF 첫 페이지와 사람 평가 결과 논의 일부를 확인했다. 실험 재현 없음.

적용할 원칙: 명료성/단순화와 의미 보존을 별도 축으로 평가한다.

적용 한계: 영어 문서와 기존 모델의 결과를 한국어 규격 성능으로 옮기지 않는다.

실험 가설: 가독성 개선과 중대한 의미 오류의 관계가 한국어 기술 문서에서도 상충하는가?

## R14. 그 많은 개발 문서는 누가 다 만들었을까 (1) 토스페이먼츠 테크니컬 라이터가 하는 일

저자: 한주연. 발행: 2024-01-23. [원문](https://toss.tech/article/tech-writer-1).

확인 상태: checked_this_run. 저자·게시일, 개발자 대상 문서·용어 정리·독자 과제 설명을 확인했다. 내부 성과 자료는 확인하지 않았다.

적용할 원칙: 개발자의 학습과 작업 성공을 문체 선호와 분리해 평가한다.

적용 한계: 개별 회사의 경험을 통제 실험이나 한국어 작성 표준으로 간주하지 않는다.

실험 가설: 용어 통일과 정보 배열이 개발자의 조건 질문 정답률에 영향을 주는가?

## R15. Extend Claude with skills

저자: Anthropic. 발행: living_document. [원문](https://code.claude.com/docs/en/skills).

확인 상태: checked_this_run. 프로젝트 .claude/skills/<name>/SKILL.md, 개인 ~/.claude/skills/<name>/SKILL.md와 지원 파일을 확인했다. 호스트 실행 미실시.

적용할 원칙: 공통 SKILL과 상대경로 참조를 함께 설치하고 필요한 파일만 읽는다.

적용 한계: 설치 경로 문서 확인은 모델 행동·지시 주입 저항·호환성 검증이 아니다.

실험 가설: 호스트 버전에 따라 모드 선택과 보호 구간 유지가 일관되는가?

## R16. Build skills

저자: OpenAI. 발행: living_document. [원문](https://learn.chatgpt.com/docs/build-skills).

확인 상태: checked_this_run. 공식 문서의 Codex .agents/skills 검색 위치, 사용자 ~/.agents/skills와 스킬 호출/참조 구조를 확인했다. 원래 developers.openai.com/codex/skills/에서 공식 리디렉션됨.

적용할 원칙: Codex 프로젝트/사용자 설치 방법과 점진적 읽기 경로를 제공한다.

적용 한계: 다른 버전·호스트의 자동 발견이나 실제 모델 출력 성공을 보장하지 않는다.

실험 가설: Lite가 연구 전체를 읽지 않으면서도 보존 조건을 지키는가?

## 프로젝트의 별도 실험

논문 초록을 읽은 일, 검사 코드 회귀 테스트, AI 초안 라벨 대비 경고 집계, 독립 사람 의미 검토와 독자 과제를 각각 보고한다. 방법은 [평가 계획](../docs/EVALUATION.md)을 따른다. 원문 문장 수 제한이나 영어 통제 어휘를 한국어 규칙으로 그대로 가져오지 않는다.
