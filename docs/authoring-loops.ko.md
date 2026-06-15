# 커스텀 루프 작성하기

Odin-Loop에는 기본 내장 루프(`spec-harness-tdd`)가 함께 제공되지만, 진짜 힘은
**루프가 곧 데이터**라는 점에 있습니다 — 직접 작성할 수 있는 YAML 파일이죠. 이
가이드는 "루프가 뭔지도 몰랐던" 상태에서 `/odin run`으로 직접 시작할 수 있는
커스텀 루프를 만드는 데까지 데려다줍니다.

코드는 한 줄도 작성하지 않습니다. 워크플로를 여러 스테이지(stage)의 목록으로
서술하면 — 각 스테이지에는 목표(goal)와 게이트(gate)가 있습니다 — 엔진이 대신
실행해 줍니다. 이 가이드를 끝까지 읽고 나면, 명령어 하나로 시작할 수 있는 나만의
루프가 손에 남습니다.

> **사전 준비물:** `odin-loop` 플러그인이 설치된 Claude Code(`/odin list`가 동작),
> 작업할 프로젝트 디렉터리, 그리고 기본적인 YAML 지식. 플러그인 설치나 일상적인
> `run`/`step`/`status` 동작 원리는 이 가이드의 범위 밖입니다 — 자세한 내용은
> `docs/features.md`를 참고하세요.

---

## 1. 루프란 무엇이고, 언제 직접 작성하나요?

**루프(loop)**는 데이터로 작성된, 반복 가능한 워크플로입니다. 엔진은 여러분의
YAML을 읽어 **스테이지(stage)**를 순서대로 밟아 나가며, 각 스테이지의
**게이트(gate)**가 "작업이 충분히 괜찮다"고 판정할 때만 다음으로 넘어갑니다.
어떤 스테이지가 게이트를 통과하지 못하면, 엔진은 앞쪽 스테이지로 되돌아가 다시
시도합니다 — 그래서 "루프"입니다.

여러분은 엔진을 프로그래밍하는 게 아니라, 하나의 *프로세스*를 서술하는 것이며,
엔진은 그것을 *강제*합니다 — 통과하지 못한 게이트를 넘어 작업이 진행되도록
내버려 두지 않습니다.

기본 내장 `spec-harness-tdd`가 실제 여러분의 작업과 맞지 않을 때 — 예를 들어 글쓰기
프로세스, 리뷰 체크리스트, 릴리스 루틴, 리서치 절차 같은 경우 — 직접 루프를
작성하세요. 작업에 명확한 단계가 있고, 각 단계 사이에 "이 정도면 됐나?"를 객관적으로
판정할 기준을 세울 수 있다면 루프로 만들기 좋은 작업입니다.

---

## 2. 핵심 개념 (용어 정리)

모든 루프 파일에서 만나게 될 용어들입니다. 전체 용어를 쉬운 말로 정리하면:

- **loop(루프)** — 워크플로 전체: `name`, `description`, 전역 `max_iterations`
  상한, 그리고 순서가 있는 `stages` 목록.
- **stage(스테이지)** — 하나의 작업 단계. `id`, `title`, `goal`(무엇을 달성해야
  하는지), `prompt`(그 스테이지를 수행하기 위해 엔진이 따르는 지시), 그리고
  `gate`를 가집니다.
- **goal(목표)** — 그 스테이지의 의도를 한 문장으로. "이 스테이지가 끝났을 때
  무엇이 참이어야 하는가."
- **gate(게이트)** — 다음으로 넘어가기 위한 조건. 게이트가 통과되기 전까지 엔진은
  그 스테이지를 넘어가지 않습니다. 게이트는 `mode`와 `check`를 가지며,
  선택적으로 `on_fail`을 가집니다.
- **gate mode(게이트 모드)** — *누가* 판정하고, 루프가 멈추는지 여부:
  - `ai` — 엔진이 check를 판정하고 통과 시 **자동으로 진행**합니다(멈추지 않음).
  - `ai+human` — 엔진이 check를 판정한 뒤, 진행 전에 **여러분의 승인을 위해
    멈춥니다**.
  - `human` — 여러분이 직접 판정합니다.
- **gate check(게이트 검사)** — 게이트가 평가하는, 테스트 가능한 단언.
  예: "`harness/`의 모든 테스트가 통과한다." 의견이 아니라 관찰 가능한 형태로
  작성하세요.
- **on_fail** — 게이트가 실패했을 때 되돌아갈 스테이지 `id`. 생략하면 같은
  스테이지를 단순히 다시 시도합니다.
- **agent** — 스테이지가 *어디서* 실행되는지. 생략하거나 `inline`이면 엔진이 직접
  실행합니다. `agent: fresh`로 설정하면 이전 대화 맥락이 없는 클린룸 서브에이전트에서
  실행됩니다 — 검사 대상 작업에 편향되면 안 되는 독립적 리뷰·감사용입니다(그 스테이지의
  `consumes` 산출물만 봅니다).
- **interview** — *선택*, 요구사항 수집 스테이지용. `interview.mode: deep`으로 설정하면
  **딥 인터뷰 플레이북**을 실행합니다: 작업의 컴포넌트를 확정(토폴로지)하고, 매 라운드
  명확도를 자가 채점해 ambiguity가 `threshold` 이하가 될 때까지 돌리며, contrarian
  챌린지를 주입하고, 자동 보조를 씁니다. §6½ 참고.
- **max_iterations** — 게이트 실패(루프백) 횟수에 대한 전역 안전 상한이며,
  해피패스 스테이지 실행은 세지 않습니다. 루프가 무한히 도는 것을 막아 줍니다.
  루프백이 이 값을 넘으면, 엔진은 다시 반복하는 대신 멈추고 보고합니다.

---

## 3. 루프 파일: 어디에 두고, 스키마는 어떤가

커스텀 루프는 YAML 파일 하나입니다. 다음 위치에 두세요:

```
<project>/.odin-loop/loops/<name>.yaml
```

`<name>`은 루프의 `name:` 필드와 일치해야 합니다. 이름으로 루프를 실행하면, 엔진은
먼저 여러분의 **프로젝트** `.odin-loop/loops/`를 확인한 뒤 **내장** 루프를
확인합니다 — 그래서 프로젝트 루프가 내장 루프를 가릴(shadow) 수 있습니다.

스키마는 위에서 아래로:

```yaml
name: my-loop            # 고유한 루프 id (파일명과 일치)
version: 1               # 정수; 호환성 깨지는 변경 시 올림
description: one-liner   # `/odin list`에 표시됨
max_iterations: 12       # 게이트 실패(루프백) 상한, 해피패스 실행은 미포함

stages:
  - id: first-stage      # 고유한 스테이지 id
    title: First Stage   # 사람이 읽는 라벨
    goal: what this stage must achieve
    prompt: |            # 스테이지를 실행하기 위해 엔진이 따르는 지시
      Do the thing. Be specific about what "done" looks like.
    consumes: [some-input.md]   # 이 스테이지가 읽는 산출물   (힌트, 선택)
    produces: [some-output.md]  # 이 스테이지가 쓰는 산출물   (힌트, 선택)
    agent: inline               # inline (기본) | fresh (클린룸 서브에이전트)
    interview:                  # 선택 — 이 스테이지를 딥 인터뷰 플레이북에 편입
      mode: deep                #   (토폴로지 + 수렴 + 챌린지 + 자동 보조).
      threshold: 0.15           #   딥 인터뷰는 interview-log.md도 produces 합니다.
      challenges: [contrarian@4, simplifier@6, ontologist@8]
      auto_assist: true
    gate:
      mode: ai           # ai | ai+human | human
      check: the observable condition that must be true to advance
      on_fail: first-stage   # 실패 시 점프할 스테이지 id (선택)
```

`consumes`와 `produces`는 스테이지 간 데이터 흐름을 문서화하는 힌트입니다. 어떤
스테이지가 어떤 산출물을 읽고 쓰는지 엔진(과 여러분)이 파악하는 데 도움을 줍니다.
`interview` 블록은 선택이며 요구사항 수집 스테이지에서만 의미가 있습니다 — §6½ 참고.

---

## 4. 스테이지 · 게이트 · 루프백 설계하기

세 가지 결정이 루프의 성패를 가릅니다.

**작업을 스테이지로 나누기.** 각 스테이지는 하나의 명확한 목표를 가지고 한 종류의
산출물을 만들어야 합니다. 두 스테이지 사이의 좋은 경계는, 자연스럽게 *계속 진행하기
전에 작업을 점검하고 싶어지는* 지점입니다. 두 단계 사이에 점검 기준을 댈 수 없다면,
그건 사실 하나의 스테이지일 가능성이 큽니다.

**게이트 모드 고르기.** 판단이 가장 중요하고 잘못 들어섰을 때 되돌리기 비싼
순간에는 `ai+human`을 쓰세요 — 보통 방향을 정하는 결정과 최종 승인이 그렇습니다.
엔진이 스스로 판정할 수 있는 기계적인 검사(빌드 통과, 모든 섹션 작성 완료)에는
`ai`를 써서, 굳이 볼 필요 없는 일에 루프가 멈춰 묻지 않도록 하세요.

**테스트 가능한 check 작성하기.** check는 취향이 아니라 관찰 가능한 것이어야
합니다. 비교해 보면:

- 나쁜 예: `check: the document reads well` — 누구도 객관적으로 통과/실패를
  가릴 수 없습니다.
- 좋은 예: `check: every section listed in the outline has prose with no TODOs`
  — 누구든 보면 알 수 있습니다.

**루프백 설계하기.** 게이트가 실패하면 `on_fail`이 어디로 갈지 결정합니다. *문제를
고칠 수 있는 가장 이른 스테이지*를 가리키세요. 테스트 스테이지가 실패하면 보통
스펙까지 거슬러 가는 게 아니라 구현 스테이지로 되돌아가야 합니다. `on_fail`을
생략하면 같은 스테이지를 다시 시도합니다. 마지막으로, `max_iterations`는 정직한
재시도 몇 번은 허용할 만큼 높게, 그러나 막힌 루프가 무한히 돌지 않고 멈춰 보고할
만큼 낮게 설정하세요 — `12`가 무난한 기본값입니다.

---

## 5. 루프를 작성하는 두 가지 방법

### (a) 직접 작성

1. `<project>/.odin-loop/loops/<name>.yaml`을 만듭니다.
2. `name`, `version`, `description`, `max_iterations`를 채웁니다.
3. `stages`를 추가하고, 각 스테이지에 `id`, `title`, `goal`, `prompt`, `gate`를
   넣습니다.
4. 저장한 뒤 검증하고 실행합니다(§7 참고).

내장된 `spec-harness-tdd.yaml`을 복사해서 고치는 것도 좋은 출발점입니다 — 그
파일 헤더에 모든 필드가 문서화되어 있습니다.

### (b) `/odin new` 사용 (가이드 인터뷰)

빈 파일에서 시작하기보다 인터뷰를 받고 싶다면, 다음을 실행하세요:

```
/odin new
```

엔진이 한 번에 한두 개씩 질문합니다:

1. 이 루프는 어떤 종류의 작업을 위한 것인가요?
2. 스테이지는 순서대로 무엇이고, 각각의 목표는 무엇인가요?
3. 각 스테이지의 게이트 check는 무엇이고 — `ai`인가요, `ai+human`인가요?
4. 스테이지가 게이트에 실패하면 어디로 되돌아가야 하나요(`on_fail`)?
5. 전역 `max_iterations` 상한은 얼마인가요?
6. 검사 대상 작업에 편향되면 안 되는 독립적 리뷰가 필요한 스테이지가 있나요? 있다면
   `agent: fresh`(클린룸 서브에이전트)로 표시됩니다.
7. 루프가 요구사항 수집 인터뷰로 시작하나요? 그렇다면 **딥 인터뷰**
   (`interview.mode: deep`)를 제안하고 `threshold`, `challenges`, `auto_assist`를
   받습니다(§6½ 참고).

그런 다음 유효한 루프 YAML을 `.odin-loop/loops/<name>.yaml`에 작성하고, 그
내용을 다시 보여 주며, `/odin run <name>`으로 시작하도록 안내합니다.

---

## 6. 실전 예제: `tech-docs` 루프

기술 문서를 작성하기 위한 완성된 커스텀 루프입니다. 문서의 방향을 잡고(brief),
개요를 짜고(outline), 초안을 쓰고(draft), 모든 주장을 사실 확인하고(fact-check),
다듬습니다(revise). 아래 YAML은 지면을 위해 축약했습니다: 모든 `id`, `title`,
`goal`, 게이트 `mode`, `on_fail`은 원문 그대로 보여 주고, 긴 `prompt` 본문과
`check` 텍스트는 (`...`로 표시하여) 줄였습니다. 전체 파일은
`.odin-loop/loops/tech-docs.yaml`에 있습니다.

```yaml
name: tech-docs
version: 1
description: Frame audience/goal -> outline -> draft -> fact-check -> revise (technical docs / README)
max_iterations: 12

stages:
  - id: brief
    title: Frame the Doc (Huginn)
    goal: Pin down audience, purpose, scope, and testable success criteria before any writing
    prompt: |
      Interview the user before writing a single line of prose ...
    produces: [brief.md]
    gate:
      mode: ai+human
      check: brief.md names a specific audience and a single clear purpose, ...

  - id: outline
    title: Outline & Structure
    goal: Lock the section structure and logical flow that will satisfy every success criterion
    prompt: |
      Design the skeleton before writing prose ...
    consumes: [brief.md]
    produces: [outline.md]
    gate:
      mode: ai+human
      check: outline.md maps every success criterion to a section and vice versa ...

  - id: draft
    title: Draft the Prose
    goal: Write complete prose for every outlined section, with no placeholders
    prompt: |
      Write the actual document into doc.md, following outline.md ...
    consumes: [brief.md, outline.md]
    produces: [doc.md]
    gate:
      mode: ai
      check: Every section in outline.md has complete prose in doc.md, no placeholders ...

  - id: fact-check
    title: Fact-Check (Gungnir - the spear that never misses)
    goal: Verify every claim, number, command, path, and code sample against reality
    prompt: |
      Treat every checkable assertion in doc.md as guilty until verified ...
    consumes: [doc.md]
    produces: [fact-check-report.md]
    agent: fresh
    gate:
      mode: ai
      check: every checkable assertion verified, zero FAIL or unverifiable items remain
      on_fail: draft

  - id: revise
    title: Revise & Sign-Off
    goal: A genuine critique and edit pass for clarity, redundancy, and audience fit
    prompt: |
      Do a real editing pass -- not a "looks good" ...
    consumes: [brief.md, outline.md, doc.md, fact-check-report.md]
    gate:
      mode: ai+human
      check: a critique pass applied with concrete edits, doc satisfies every success criterion
```

이렇게 설계한 이유:

- **`brief`와 `outline`은 `ai+human`입니다.** 대상/목표를 잡는 것과 구조 설계는
  잘못 들어섰을 때 가장 비싼 지점이므로, 어떤 산문도 쓰기 전에 루프가 멈춰
  여러분의 승인을 받습니다.
- **`draft`와 `fact-check`는 `ai`입니다.** 이들은 기계적입니다: "모든 섹션이
  작성됐는가?", "모든 주장이 검증됐는가?" 엔진이 둘 다 판정해 자동으로 진행할 수
  있으므로 여러분을 방해하지 않습니다.
- **`fact-check`는 `on_fail: draft`입니다.** 주장이 사실로 확인되지 않으면 고칠
  곳은 산문이므로, 루프는 `brief`까지가 아니라 `draft`로 되돌아갑니다.
- **`fact-check`는 `agent: fresh`로 실행됩니다.** 클린룸 서브에이전트가 초안이 어떻게
  작성됐는지 전혀 모르는 상태에서 — `doc.md`만 보고 — 모든 주장을 다시 검증하므로,
  자기 추론을 통과시켜 주지 못합니다.
- **`revise`는 `ai+human`입니다.** 마지막 스테이지는 완성된 문서에 대한 여러분의
  최종 승인입니다.

---

## 6½. 더 깊이: 딥 인터뷰 (선택)

루프가 요구사항을 *당신에게 인터뷰하는* 스테이지로 시작한다면, `interview:` 블록을
추가해 평범한 프롬프트에서 **딥 인터뷰 플레이북**으로 업그레이드할 수 있습니다:

```yaml
- id: interview
  title: Deep Interview (Huginn)
  goal: Turn a vague request into testable acceptance criteria
  interview:
    mode: deep                 # 프롬프트만이 아니라 플레이북을 실행
    threshold: 0.15            # 자가 채점 ambiguity ≤ 이 값일 때 종료 (0..1)
    challenges: [contrarian@4, simplifier@6, ontologist@8]   # contrarian 프로브
    auto_assist: true          # 읽기 전용 후보답 / opt-out 서브에이전트
  prompt: |
    (도메인 프레이밍만 — 어떤 차원을 캐물을지; 절차는 플레이북이 담당)
  produces: [spec.md, interview-log.md]
  gate:
    mode: ai+human
    check: >
      interview-log.md의 ambiguity ≤ threshold; 모든 토폴로지 컴포넌트가 spec.md에서
      테스트 가능한 기준으로 커버됨; 미해결 blocking 질문 없음.
```

각 노브의 역할:

- **`mode: deep`** — 유일한 필수 필드. 엔진이 프롬프트만 따르는 대신 플레이북
  (`skills/loop-engine/deep-interview.md`)을 실행하게 합니다: 작업을 **1~6개
  컴포넌트**(토폴로지)로 열거·확정한 뒤, 한 번에 한 질문씩 돌리며 매 라운드 **명확도를
  자가 채점**합니다.
- **`threshold`** — 게이트. 매 라운드 엔진이 `ambiguity = 1 − Σ(clarity × weight)`를
  `interview-log.md`에 기록하고, ambiguity ≤ `threshold`가 되어야 전진합니다. 낮을수록
  엄격(`0.15`가 무난한 기본값, 빠른 통과는 `0.30`). 이 점수는 계산된 지표가 아니라
  정직한 **자가 평가**입니다 — Odin-Loop엔 코드 런타임이 없으므로 — 가치는 거짓
  정밀도가 아니라 기록되어 들여다볼 수 있는 추적에 있습니다.
- **`challenges`** — 명시된 라운드에 고정 각도의 프로브를 주입: `contrarian`("반대가
  참이라면?"), `simplifier`("가치를 지키는 가장 단순한 버전은?"), `ontologist`("이건
  사실 무엇인가?").
- **`auto_assist`** — 읽기 전용 서브에이전트가 (그린필드 질문에) 순위 매긴 후보 답을
  제안하거나, 당신이 건너뛴 질문을 해소하게 합니다. 결코 대신 결정하지는 않습니다.

딥 인터뷰는 항상 `inline`이고(당신과 대화해야 하므로) `spec.md`와 함께
**`interview-log.md`를 produces** 합니다. 위처럼 게이트 `check`를 ledger 기준으로
작성하세요.

---

## 7. 검증하고, 실행하고, 다음으로

실행하기 전에, 엔진이 검증하는 규칙에 맞춰 YAML을 점검하세요:

- 모든 **스테이지 `id`는 고유**해야 합니다.
- 모든 **`on_fail`은 같은 루프 안의 실제 스테이지 `id`를 가리켜야** 합니다.
- 모든 **게이트는 `mode`와 `check`를 모두** 가져야 합니다.
- 모든 **`agent`는 `inline` 또는 `fresh`** 중 하나여야 하며, `agent: fresh` 스테이지는
  **비어 있지 않은 `consumes`를 선언**해야 하고(유일한 입력 채널), 사용자와 대화하는
  스테이지는 절대 `fresh`가 아닙니다.
- 모든 **`interview.mode: deep`** 스테이지는 `agent: fresh`가 아니고, `produces`에
  `interview-log.md`를 포함하며, `threshold`가 (0, 1) 범위의 수이고, 모든 `challenges`
  항목이 `contrarian|simplifier|ontologist@<round>` 형식입니다.

이걸 손으로 점검할 필요는 없습니다 — 함께 제공되는 검증기가 결정론적으로 확인합니다:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_loop.py" .odin-loop/loops/<name>.yaml
```

blocking 에러가 있으면 출력하고(exit `1`), 없으면 루프가 유효함을 확인합니다(exit `0`).
`/odin new`와 `/odin run`이 시작 전에 대신 실행해 줍니다. (PyYAML이 필요하며, 설치되어
있지 않으면 exit `3`로 위 체크리스트로 폴백합니다.)

그런 다음 엔진이 루프를 인식하는지 확인하고 시작하세요:

```
/odin list              # 여러분의 루프가 description과 스테이지 수와 함께 표시됨
/odin run <name>        # 첫 스테이지부터 루프 시작
/odin status            # 언제든 현재 실행 상태 확인
```

`/odin run <name>`을 실행하면, 엔진은 실행(run)을 생성하고, 첫 스테이지를 현재
스테이지로 설정한 뒤, 그것을 실행하고 게이트를 평가합니다. 그 첫 게이트가
`ai+human`이면 루프는 멈춰 여러분의 `/odin run` 승인을 기다리고, `ai`이면 자동으로
진행합니다.

**다음으로 (이 가이드의 범위 밖):**

- 과거 실행을 바탕으로 루프를 개선하려면 `/odin refine`과 **muninn** 스킬을
  참고하세요 — 작성과는 별개의 워크플로입니다.
- `run`, `step`, `status`의 전체 동작 원리는 `docs/features.md`와
  `docs/design.md`를 참고하세요.
