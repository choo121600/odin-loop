# Odin-Loop

[English](README.md) | **한국어**

> 나만의 AI 개발 워크플로우 *루프*를 직접 만들고, 실행하고, 다듬는다 — 수정 가능한 데이터로.

대부분의 "AI 개발 워크플로우" 도구는 **고정된 하나의 루프**를 강요합니다. Odin-Loop는
루프 그 자체를 1급 시민, 즉 *수정 가능한 산출물*로 다룹니다 — 엔진이 읽고 실행하는 YAML
파일이죠. 강력한 기본 루프가 함께 제공되며, `/odin new`로 자신만의 루프를 만들고 다듬을
수 있습니다.

```
deep interview → plan → harness design → harness verify → implement → test → clean review
   (Huginn)     (planner) (executor)    (critic·Gungnir) (executor) (executor)  (reviewer)
```

이름은 신화에서 따왔고, 그대로 아키텍처에 매핑됩니다:

| 신화 | 역할 | Odin-Loop에서 |
| --- | --- | --- |
| **오딘(Odin)** | 사냥을 이끄는 지혜의 추구자 | 루프를 구동하는 엔진 |
| **후긴(Huginn, "사고")** | 추론의 까마귀 | deep-interview 단계 |
| **무닌(Muninn, "기억")** | 기억의 까마귀 | 세션 마이닝 교정기 (`/odin refine`) |
| **궁니르(Gungnir)** | 빗나가지 않는 창 | 하니스 검증 게이트 |

## 기본 루프가 이렇게 설계된 이유

- **deep interview 먼저** — AI 코딩 실패의 대부분은 코딩 실패가 아니라 *의도* 실패입니다.
  인터뷰는 작업의 **컴포넌트**(토폴로지)를 확정하고, 고정된 차원 집합을 훑으며, 매 라운드
  **명확도를 자가 채점**해 ambiguity가 임계값 아래로 떨어질 때까지 — 그 과정에서 contrarian
  챌린지와 자동 보조를 주입하며 — 돌립니다. 코드를 쓰기 전에 모호한 요청을 *테스트 가능한
  acceptance criteria*로(구조화된 `spec.md`에 담고, 수렴 추적은 `interview-log.md`에) 바꿉니다.
  ([설계 → 딥 인터뷰](docs/design.ko.md#딥-인터뷰-후긴) 참고.)
- **구현보다 하니스 먼저** — criteria가 실행 가능한 테스트가 되므로, "완료"에 객관적
  정의가 생깁니다.
- **하니스 자체를 검증 (궁니르)** — 대부분의 도구가 건너뛰는 단계입니다. 항상 통과하는
  테스트는 아무것도 증명하지 못합니다. 고의로 틀린 stub을 돌려 *최소 1개 테스트가 실패*
  하도록 요구함으로써, 하니스에 "이빨"이 있음을 증명합니다.
- **그다음 구현하고 테스트** — 검증된 하니스를 타겟으로 구현하고, 실패 시 루프백하되
  `max_iterations` 상한으로 제한합니다.
- **깨끗한 에이전트로 리뷰** — 마지막 `reviewer` 역할 스테이지(클린룸, 이전 맥락 없음)가
  어떻게 만들어졌는지에 대한 기억 없이 결과를 리뷰해, 하니스로 인코딩할 수 없는 것(놓친
  엣지 케이스, 스코프 크리프)을 잡아냅니다. 객관적으로 정의된 *blocking* 지적은 `implement`로 루프백하고
  (수정 시 회귀 테스트를 추가), 스테이지는 당신의 승인을 위해 멈춥니다.

## 설치

```
/plugin marketplace add choo121600/odin-loop
/plugin install odin-loop@odin-loop
```

## 빠른 시작

첫 `/odin run` 시 Odin-Loop는 어떤 루프를 쓸지 묻고(기본 `spec-harness-tdd`) 딥
인터뷰를 시작합니다 — 코드를 쓰기 전에 요청을 테스트 가능한 acceptance criteria로
바꿉니다.

```
/odin run        # 활성 런 없음 → 루프 선택 후 인터뷰
/odin status     # 런 위치 확인
```

모든 `ai+human` 게이트에서 멈춥니다. `/odin run`을 다시 실행하면 승인, 피드백을
입력하면 그 단계를 수정합니다.

## 사용법

```
/odin run            # 런 시작 또는 이어가기 (사람 승인 게이트에서 멈춤)
/odin step <stage>   # 특정 단계만 다시 실행
/odin status         # 현재 런 상태 보기
/odin list           # 사용 가능한 루프 목록
/odin new            # 인터뷰를 통해 나만의 루프 작성
/odin refine [loop]  # 과거 작업을 분석해 루프 수정안 제안 (무닌)
```

### 하이브리드 실행

`/odin run`은 루프를 자동으로 진행하되, **`ai+human` 게이트에서 멈춰** 당신이 통제권을
유지하게 합니다. 멈춘 단계를 승인하려면 `/odin run`을 다시 실행하면 되고, 수정이
필요하면 그냥 피드백을 입력해 그 단계를 다시 돌리고 재검증하면 됩니다.

### 무닌 — 스스로 다듬어지는 루프

`/odin refine`은 당신의 Odin-Loop 런 기록과 Claude Code 세션 기록을 마이닝해, 당신이
어디서 단계를 건너뛰거나 재작업하거나 루프백하는지 찾아낸 뒤 **루프 YAML에 대한 구체적인
수정안**을 제안합니다 (예: "`implement` 단계가 자주 루프백함 → `interview` 게이트를
강화"). 번들된 분석기는 집계 신호만 추출하며(메시지 내용은 절대 읽지 않음), **승인 없이는
아무것도 적용되지 않습니다** — `/odin refine apply`로 수락합니다. 루프가 당신의 실제
작업 방식으로부터 배웁니다.

## 문서

- [설계](docs/design.ko.md) — 아키텍처, loop-as-data 모델, 게이트·상태
- [기능](docs/features.ko.md) — 모든 명령, 기본 루프, 무닌
- [시나리오](docs/scenarios.ko.md) — 엔드투엔드 워크스루
- [커스텀 루프 작성](docs/authoring-loops.ko.md) — 직접 루프를 YAML로 작성

## 루프는 데이터다

루프는 YAML 파일입니다 (전체 주석이 달린 스키마는
[`plugins/odin-loop/loops/spec-harness-tdd.yaml`](plugins/odin-loop/loops/spec-harness-tdd.yaml)
참고). 핵심만 보면:

```yaml
name: my-loop
version: 1
max_iterations: 12
stages:
  - id: design
    goal: ...
    gate:
      mode: ai+human        # ai = 자동 진행 · ai+human = 승인 위해 멈춤
      check: <전진하기 위한 testable 조건>
      on_fail: <실패 시 돌아갈 stage id>   # 선택
```

기본 루프는 `plugins/odin-loop/loops/`에, 커스텀 루프는 프로젝트의 `.odin-loop/loops/`에
위치합니다. 런 상태는 `.odin-loop/runs/`에 저장됩니다.

### 스테이지 역할

각 스테이지는 `agent`로 **누가** 실행할지 지정할 수 있습니다: `inline`(엔진 자신),
`fresh`(범용 클린룸 서브에이전트), 또는
[`plugins/odin-loop/agents/`](plugins/odin-loop/agents/)에 들어 있는 다섯 가지
재사용 역할 중 하나:

| `explore` | `planner` | `executor` | `critic` | `reviewer` |
| --- | --- | --- | --- | --- |
| 읽기 전용 정찰 | spec → 계획 | 구현·테스트 | 적대적 검증 (Gungnir) | 클린 리뷰 |

`explore` / `critic` / `reviewer`는 기본적으로 **fresh**(클린룸)로, `planner` /
`executor`는 **inline**으로 실행됩니다. 스테이지별로
`agent: { role: reviewer, fresh: false }`처럼 기본값을 덮어쓸 수 있습니다. 역할은
일꾼이 *어떻게* 행동할지를 정할 뿐, 스테이지의 게이트와 산출물은 YAML에 그대로 남습니다.

## 상태

`v0.6.0` — **명명된 스테이지 역할**: 스테이지의 `agent`를 이제 다섯 가지 재사용 페르소나
— `explore` / `planner` / `executor` / `critic` / `reviewer`(`plugins/odin-loop/agents/`에
수록) — 중 하나로 지정할 수 있고, 각자 기본 클린룸/inline 컨텍스트를 가지며
`agent: { role, fresh }`로 덮어쓸 수 있습니다. 기본 루프도 스테이지들을 이 역할로 실행합니다.
이전: v0.5.0 구현 **계획** 스테이지; v0.4.0 **딥 인터뷰 플레이북**(멀티 컴포넌트 토폴로지,
매 라운드 명확도 자가 채점→ambiguity 임계값 수렴, contrarian/simplifier/ontologist 챌린지,
자동 보조) + 결정론적 루프 검증기(`scripts/validate_loop.py`); v0.3.0 클린룸 **review**
스테이지 + `agent: inline | fresh`; v0.2.0 인터뷰 심화(8개 차원 게이트 + 구조화된 `spec.md`);
v0.1.1 엔진 + 기본 루프 + 커스텀 루프 작성 + 무닌(`/odin refine`) 세션 마이닝 교정.

## 라이선스

MIT
