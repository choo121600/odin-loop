# Odin-Loop — 시나리오

[English](scenarios.md) | **한국어**

세 가지 엔드투엔드 워크스루. 정확한 출력이 아니라 세션의 *형태*를 보여줍니다.

## 시나리오 1 — 기본 루프로 실행

뭔가 만들고 싶지만 요구사항이 아직 모호합니다.

```
/odin run
  → 활성 런 없음 → 엔진이 어떤 루프인지 물음 (기본: spec-harness-tdd)
  → interview: 핵심 질문 몇 개; spec.md가 테스트 가능한 기준으로 채워짐
  → ⏸ ai+human 게이트: 스펙 검토 후 /odin run 으로 승인
/odin run
  → plan: spec.md → plan.md — 빌드 단위, 파일 타겟, 빌드 순서 (inline)
  → ⏸ ai+human 게이트: 계획 검토 후 /odin run 으로 승인
/odin run
  → harness-design: 각 기준이 테스트가 됨 (아직 구현 없으니 red)
  → harness-verify (궁니르): 고의로 틀린 스텁이 ≥1 테스트를 실패시켜야 함 (ai, 자동)
  → implement: 하니스를 타겟으로, 계획의 빌드 순서를 따라 구현 · test: 실행
  → 테스트 실패 → implement로 루프백 (max_iterations로 제한)
  → review (새 에이전트, 이전 맥락 없음): src/를 spec.md와 대조 검토
  → blocking 지적(스펙/엣지 케이스/보안) → implement로 (수정 시 회귀 테스트 추가); 없으면 → ⏸ ai+human 승인 → done
```

인터뷰가 핵심입니다 — 대부분의 실패는 의도 실패이므로, "완료"에 테스트 가능한 정의가
생기기 전까지 루프는 코드 작성을 거부합니다.

## 시나리오 2 — 커스텀 루프 작성 (`/odin new`)

기본 루프가 당신의 작업(예: 문서나 리서치 프로세스)에 맞지 않습니다.

```
/odin new
  → interview: 어떤 스테이지를 어떤 순서로? 각 스테이지의 goal은?
  → 각 스테이지: 게이트 check, 그리고 ai 인가 ai+human 인가?
  → 각 스테이지는 실패 시 어디로 루프백하나 (on_fail)?
  → max_iterations 상한은?
  → 독립적 리뷰가 필요한 스테이지가 있나? → agent: fresh로 표시
  → .odin-loop/loops/<name>.yaml 작성(검증됨) 후 /odin run <name> 제안
```

루프가 그저 데이터이기 때문에, 당신의 커스텀 루프는 기본 루프와 정확히 같은 엔진과
게이트를 통해 실행됩니다.

## 시나리오 3 — 루프 교정 (`/odin refine`)

몇 번 실행한 뒤, 같은 스테이지를 계속 재작업하고 있음을 알아챕니다.

```
/odin refine
  → 분석기가 런 기록 + 세션 집계를 읽음 (메시지 내용은 절대 안 읽음)
  → 예: "implement가 자주 루프백" → 제안: interview 게이트 강화
  → before/after YAML diff가 담긴 교정 리포트 작성 — 아직 아무것도 적용 안 됨
/odin refine apply
  → 승인된 수정을 적용하고 루프 version을 올림
```

무닌은 바깥 루프를 닫습니다 — 프로세스가 당신의 실제 작업 방식에서 배우고, 모든 변경은
당신이 승인합니다.

---

함께 보기: [설계](design.ko.md) · [기능](features.ko.md) · [← README](../README.ko.md)
