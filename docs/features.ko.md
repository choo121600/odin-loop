# Odin-Loop — 기능

[English](features.md) | **한국어**

Odin-Loop가 할 수 있는 일을 명령 단위로.

## 명령 표면

모든 것은 `/odin <서브커맨드>`로 구동됩니다:

| 명령 | 하는 일 |
| --- | --- |
| `/odin run` | 활성 런 시작 또는 이어가기. `ai` 게이트는 자동 진행, `ai+human` 게이트에서 멈춤. |
| `/odin step <stage>` | id로 정확히 한 스테이지만 재실행(자동 진행 안 함). 수동 override / 재실행. |
| `/odin status` | 활성 런의 루프·태스크·현재 스테이지·히스토리 체크리스트 출력. |
| `/odin list` | 사용 가능한 루프 정의(프로젝트 + 기본)를 스테이지 수와 함께 나열. |
| `/odin new` | 인터뷰로 새 커스텀 루프를 작성해 `.odin-loop/loops/`에 기록. |
| `/odin refine [loop]` | 과거 런·세션을 마이닝해 루프 수정안 제안(무닌). |
| `/odin refine apply` | 가장 최근 교정 제안을 적용. |

`run`/`step`/`status`/`list`/`new`는 엔진이, `refine`은 무닌 스킬이 처리합니다.

## 하이브리드 실행

`/odin run`은 루프를 스스로 구동하되 **모든 `ai+human` 게이트에서 멈춰**, 중요한 결정의
통제권을 당신이 쥐게 합니다. 멈춘 스테이지를 승인하려면 `/odin run`을 다시 실행하세요.
수정하려면 그냥 피드백을 입력하면 됩니다 — 스테이지가 당신의 변경을 반영해 다시 돌고
재검증됩니다. 루프백은 `max_iterations`로 제한됩니다.

## 기본 루프: `spec-harness-tdd`

기본 제공 루프는 스펙 주도·테스트 우선 규율을 인코딩합니다:

```
interview → harness-design → harness-verify → implement → test
 (Huginn)                      (Gungnir)            ↑__________|
```

1. **interview** — 모호한 요청을 구조화된 `spec.md`로: 근본 목표를 확인하고 여덟 가지
   차원(동작·실패 모드·데이터·의존성·제약 등)을 훑어 모든 요구사항을 테스트 가능한
   acceptance criteria로 환원. 게이트는 표현뿐 아니라 커버리지까지 검사 (`ai+human`).
2. **harness-design** — 각 기준을 실행 가능한 테스트로 번역 (`ai`).
3. **harness-verify** — 하니스에 이빨이 있음을 증명: 고의로 틀린 스텁이 최소 1개
   테스트를 실패시켜야 함 (`ai+human`).
4. **implement** — 테스트를 약화하지 않고 검증된 하니스를 타겟으로 구현 (`ai`).
5. **test** — 하니스 실행, 실패 시 `implement`로 루프백 (`ai`).

## 나만의 루프 작성

`/odin new`는 스테이지, 게이트(`ai` vs `ai+human`), `on_fail` 루프백을 인터뷰한 뒤
유효한 루프 YAML을 작성합니다. 엔진은 저장 전에 스테이지 id 유일성, 모든 `on_fail`이
실제 스테이지를 가리키는지, 모든 게이트에 mode와 check가 있는지 검증합니다.

## 무닌 — 자기 교정

`/odin refine`은 번들된 분석기를 런 기록과 원시 세션 기록에 돌려(집계만 — 메시지 내용은
절대 읽지 않음) 루프 YAML에 대한 구체적이고 최소한의 수정안을 제안합니다 — 예컨대 뒷
단계가 자주 루프백하면 앞 게이트를 강화. `/odin refine apply`를 실행하기 전엔 아무것도
적용되지 않습니다.

---

함께 보기: [설계](design.ko.md) · [시나리오](scenarios.ko.md) · [← README](../README.ko.md)
