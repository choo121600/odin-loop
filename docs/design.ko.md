# Odin-Loop — 설계

[English](design.md) | **한국어**

Odin-Loop가 어떻게 구성되고 왜 그런지. 나머지 전부가 따라 나오는 단 하나의 생각:
**루프는 코드가 아니라 데이터다.**

## 루프는 데이터다

워크플로우 루프는 YAML 파일입니다. 엔진은 그 파일을 읽어 선언된 스테이지를 그대로
실행하며, 특정 워크플로우를 하드코딩하지 않습니다. YAML을 바꾸면 프로세스가 바뀝니다 —
엔진 코드는 그대로입니다. 강력한 기본 루프를 제공하면서도 `/odin new`로 사용자가 자기
루프를 작성하고, `/odin refine`으로 무닌이 수정안을 제안할 수 있는 이유가 이것입니다.

기본 루프([`spec-harness-tdd.yaml`](../plugins/odin-loop/loops/spec-harness-tdd.yaml))가
스키마의 레퍼런스이며, 파일 머리말에 모든 필드가 문서화돼 있습니다.

## 등장인물 (신화 → 아키텍처)

| 신화 | Odin-Loop에서의 역할 |
| --- | --- |
| **오딘(Odin)** | 루프를 구동하는 엔진 |
| **후긴(Huginn, "사고")** | 딥 **인터뷰** 단계 — 의도를 테스트 가능한 기준으로 환원 |
| **무닌(Muninn, "기억")** | 세션 마이닝 교정기 (`/odin refine`) |
| **궁니르(Gungnir)** | 빗나가지 않는 창 — **harness-verify** 게이트 |

후긴과 궁니르는 *루프 안의 스테이지*이고, 무닌은 루프 자체를 수정하는 *바깥* 루프입니다.

## 스테이지와 게이트

각 스테이지는 `goal`, 엔진이 따르는 `prompt`, 선택적 `consumes` / `produces` 산출물
힌트, 선택적 `agent` 실행 컨텍스트, 그리고 전진 조건인 **게이트**를 가집니다:

```yaml
- id: review
  gate:
    mode: ai+human        # ai = 엔진이 판정·자동 진행 · ai+human = 승인 위해 멈춤
    check: <테스트 가능한 단언>
    on_fail: implement        # 실패 시 점프할 스테이지 id (생략 = 같은 스테이지 재시도)
```

- `mode: ai` — 엔진이 `check`를 정직하게 판정하고 자동으로 진행합니다.
- `mode: ai+human` — 엔진이 판정한 뒤 당신의 승인을 위해 **멈춥니다**.
- `on_fail` — 실패 시 루프백할 스테이지 id.
- `agent: fresh` — 스테이지를 이전 대화 맥락이 없는 클린룸 서브에이전트에서 실행합니다.
  런의 나머지가 편향시킬 수 없는 독립적 리뷰/감사용입니다(그 스테이지의 `consumes`
  산출물만 봅니다). 생략하거나 `inline`이면 엔진이 직접 실행합니다.
- 전역 **`max_iterations`** 가 게이트 실패(루프백) 수를 제한해, 실패하는 루프가 무한히
  돌지 않고 보고하게 합니다; 해피패스 실행은 세지 않습니다.

게이트는 정직하게 판정해야 합니다 — 무조건 통과시키는 게이트는 아무것도 증명하지 못합니다.

## 런 상태 (`state.json`)

각 런은 상태를 저장해 세션을 넘어 이어갈 수 있습니다. 핵심 필드:

```json
{
  "run_id": "20260614-143501-spec-harness-tdd",
  "loop": "spec-harness-tdd",
  "status": "running | awaiting_approval | done | failed",
  "current_stage": "interview",
  "iterations": { "implement": 2, "test": 2 },
  "total_iterations": 4,
  "max_iterations": 15,
  "history": [
    { "stage": "interview", "result": "pass", "gate": "approved", "at": "..." },
    { "stage": "review", "result": "pass", "gate": "approved", "at": "...", "agent": "fresh" }
  ]
}
```

`current_stage`는 런이 재개되는 지점, `history`는 게이트 결정의 감사 추적,
`total_iterations`는 루프백마다 `max_iterations`와 비교됩니다.

## 산출물이 어디 있나

| 대상 | 경로 |
| --- | --- |
| 기본 루프 | `plugins/odin-loop/loops/*.yaml` |
| 커스텀 루프 | `.odin-loop/loops/*.yaml` (프로젝트 내) |
| 런 상태·문서 | `.odin-loop/runs/<run-id>/` |
| 런 하니스·스텁 | `.odin-loop/runs/<run-id>/harness/` (gitignored) |
| 출시 산출물 | 실제 프로젝트 트리 (`src/`, 커밋되는 테스트, 문서) |

`.odin-loop/`는 gitignore되어 있어, 런 한정 스캐폴딩이 커밋에 새지 않습니다.

## 루프 해석 우선순위

루프 이름이 참조되면 엔진은 **프로젝트** `.odin-loop/loops/`를 먼저 확인하고, 그다음
**기본** `plugins/odin-loop/loops/`를 확인합니다. 그래서 프로젝트는 플러그인을 건드리지
않고 루프를 덮어쓰거나 추가할 수 있습니다.

---

함께 보기: [기능](features.ko.md) · [시나리오](scenarios.ko.md) · [← README](../README.ko.md)
