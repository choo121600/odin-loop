# Odin-Loop — 설계

[English](design.md) | **한국어**

Odin-Loop가 어떻게 구성되고 왜 그런지. 나머지 전부가 따라 나오는 단 하나의 생각:
**루프는 코드가 아니라 데이터다.**

## 루프는 데이터다

워크플로우 루프는 YAML 파일입니다. 엔진은 그 파일을 읽어 선언된 스테이지를 그대로
실행하며, 특정 워크플로우를 하드코딩하지 않습니다. YAML을 바꾸면 프로세스가 바뀝니다 —
엔진 코드는 그대로입니다. 강력한 기본 루프를 제공하면서도 `/odin-loop:odin new`로 사용자가 자기
루프를 작성하고, `/odin-loop:odin refine`으로 무닌이 수정안을 제안할 수 있는 이유가 이것입니다.

기본 루프([`spec-harness-tdd.yaml`](../plugins/odin-loop/loops/spec-harness-tdd.yaml))가
스키마의 레퍼런스이며, 파일 머리말에 모든 필드가 문서화돼 있습니다.

## 등장인물 (신화 → 아키텍처)

| 신화 | Odin-Loop에서의 역할 |
| --- | --- |
| **오딘(Odin)** | 루프를 구동하는 엔진 |
| **후긴(Huginn, "사고")** | 딥 **인터뷰** 단계 — 의도를 테스트 가능한 기준으로 환원 |
| **무닌(Muninn, "기억")** | 세션 마이닝 교정기 (`/odin-loop:odin refine`) |
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
- `agent` — *누가* 스테이지를 실행하는지. 생략하거나 `inline`이면 엔진이 직접 실행하고,
  `fresh`이면 이전 대화 맥락이 없는 클린룸 서브에이전트에서 실행합니다 — 런의 나머지가
  편향시킬 수 없는 독립적 리뷰/감사용입니다(그 스테이지의 `consumes` 산출물만 봅니다).
  `agent`는 다섯 가지 재사용 가능한 **역할(role)** 중 하나를 지정할 수도 있습니다 —
  `explore`(읽기 전용 정찰, fresh), `planner`(스펙 → 빌드 계획, inline),
  `executor`(하니스/구현/테스트, inline), `critic`(적대적 검증, fresh),
  `reviewer`(클린 리뷰, fresh). 각 역할은 `plugins/odin-loop/agents/<role>.md`에
  제공되는 페르소나입니다. 역할은 기본 컨텍스트를 쓰는 단순 문자열이거나, 그것을 덮어쓰는
  `{ role, fresh }`로 씁니다. 역할은 워커가 *어떻게* 행동하는지를 규정하며, 스테이지의
  `goal`/`gate`/`prompt`/`produces`가 여전히 권위를 가집니다.
- 전역 **`max_iterations`** 가 게이트 실패(루프백) 수를 제한해, 실패하는 루프가 무한히
  돌지 않고 보고하게 합니다; 해피패스 실행은 세지 않습니다.

게이트는 정직하게 판정해야 합니다 — 무조건 통과시키는 게이트는 아무것도 증명하지 못합니다.

## 딥 인터뷰 (후긴)

요구사항 수집 스테이지는 `interview.mode: deep`을 선언해 **딥 인터뷰 플레이북**을
선택할 수 있습니다. 플레이북
([`skills/loop-engine/deep-interview.md`](../plugins/odin-loop/skills/loop-engine/deep-interview.md))은
인터뷰를 "충분해 보일 때까지 묻기"에서 **측정 가능한 루프**로 바꿉니다:

- **토폴로지(Topology)** — Round 0에서 작업을 1~6개 컴포넌트로 열거하고 당신과 확정해,
  잘 설명된 부분이 모호한 형제 컴포넌트를 가리지 못하게 합니다.
- **수렴(Convergence)** — 매 라운드 차원별 명확도를 자가 채점하고
  `ambiguity = 1 − Σ(clarity × weight)`를 `interview-log.md`에 기록합니다; 게이트는
  ambiguity가 설정된 `threshold` 이하일 때만 전진합니다. Odin-Loop에는 코드 런타임이
  없으므로 이 점수는 **계산된 지표가 아니라 엔진의 정직한 자가 평가**입니다 — 가치는
  거짓 정밀도가 아니라, 기록되어 들여다볼 수 있는 추적에 있습니다.
- **챌린지(Challenges)** — 정해진 라운드에 contrarian / simplifier / ontologist 프로브를
  주입해, 형성 중인 스펙을 고정된 각도에서 공격합니다.
- **자동 보조(Auto-assist)** — 읽기 전용 서브에이전트가 (그린필드) 순위 매긴 후보 답을
  제안하거나, 당신이 건너뛴 질문을 해소합니다 — 결코 대신 결정하지는 않습니다.

스테이지 `prompt`는 여전히 도메인 프레이밍을 제공하고, 플레이북은 절차를 제공합니다.
`spec.md`는 산출물, `interview-log.md`는 게이트가 읽는 근거입니다.

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
  "interview": { "threshold": 0.15, "rounds": 4, "ambiguity": 0.13, "topology": ["Ingestion", "Export"] },
  "history": [
    { "stage": "interview", "result": "pass", "gate": "approved", "at": "..." },
    { "stage": "review", "result": "pass", "gate": "approved", "at": "...", "agent": "fresh" }
  ]
}
```

`current_stage`는 런이 재개되는 지점, `history`는 게이트 결정의 감사 추적,
`total_iterations`는 루프백마다 `max_iterations`와 비교됩니다. 선택적 `interview`
객체는 딥 인터뷰 스테이지에서만 나타나며 그 수렴 상태를 반영합니다
([딥 인터뷰](#딥-인터뷰-후긴) 참고).

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
