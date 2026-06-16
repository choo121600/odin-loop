# 자율 루프 스케줄링 (Hermóðr)

[English](scheduling.md) | **한국어**

> Hermóðr는 오딘의 전령 — 오딘의 심부름을 정해진 시각에 달리는 Odin-Loop의 부분입니다.
> **완전 자율** 루프(사람 게이트가 없는 루프)를 OS 스케줄러에 등록해 **무인으로** 발화시키고,
> 매 틱을 굴리는 러너 역할도 합니다.

## 개요

`/odin run`은 당신을 운전석에 둡니다 — 모든 `ai+human` 게이트에서 승인을 위해 멈추죠. 그런데
어떤 루프는 **사람 게이트가 아예 없습니다** — 모든 게이트가 `ai`라 처음부터 끝까지 스스로
돕니다(일일 보드 루프, PR 머지 루프, audit-to-issues 루프). 이런 루프가 Hermóðr가 스케줄에
올릴 수 있는 대상입니다.

모델은 한 줄입니다:

> Hermóðr는 **사람을 위해 절대 멈추지 않는 루프만** 스케줄합니다. 그래서 무인 실행이 체크포인트를
> 몰래 자동 승인하는 일이 없습니다. *사람은 `ai+human` 게이트에서 운전대를 쥔다* 는 원칙이
> **구조적으로** 보존됩니다 — 사람 게이트가 있는 루프는 그냥 거부됩니다.

스케줄은 명시적 2단계입니다: **`register`** 는 스케줄을 데이터로 기록하고, **`install`** 이 그걸
OS 스케줄러(macOS launchd 또는 crontab 항목)에 연결합니다. 이 분리 덕에 시스템을 건드리기 전에
스케줄을 검토할 수 있습니다.

## 사전 준비

- **Odin-Loop 설치** 및 동작(`/odin run`이 루프를 굴려 줌).
- 스케줄할 **완전 자율 루프** — 모든 게이트 `ai`, `interview` 단계 없음. [스케줄 가능한
  루프](#스케줄-가능한-루프)를 보세요.
- **`claude` CLI 로그인** — 스케줄 실행은 헤드리스 `claude -p` 프로세스이고 기존 인증을 씁니다.
- **macOS**(launchd 사용) 또는 **Linux**(crontab 사용).

## 스케줄 가능한 루프

루프는 사람을 위해 절대 멈추지 않을 때만 **스케줄 가능**합니다: **모든 게이트가 `ai`**(`ai+human`
이나 `human` 없음)이고 **어떤 단계도 `interview`를 돌리지 않을** 때. 그 외는 거부됩니다 —
등록하면 오지 않을 승인을 영원히 기다리거나, 이유가 있어 존재하는 체크포인트를 몰래 자동
승인하게 되니까요.

`register`가 이 검사를 대신 수행하고 실패하는 루프는 거부합니다. 미리 확인하려면 검증기를 직접
실행하세요(`$CLAUDE_PLUGIN_ROOT`는 설치된 플러그인의 루트):

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/validate_loop.py" --schedulable <경로/루프.yaml>
# exit 0 → 스케줄 가능 · exit 1 → 불가(어느 단계가 막는지 출력)
```

선이 떨어지는 자리가 정확합니다. Odin-Loop 기본 루프 중 `audit-to-issues`, `daily-issue-plan`,
`pr-review-merge`는 스케줄 가능하고, 의도를 모으거나 사인오프를 받는 루프 —
`daily-issue-run`(`triage` 게이트), `tech-docs`(`brief` 게이트),
`spec-harness-tdd`(interview / plan / review) — 는 불가합니다.

### 사람 게이트 루프를 굳이 스케줄하려면?

**autonomous 변종**을 작성하세요. "루프는 데이터"이니, 사람 게이트를 `ai`로 낮춘(멈추는 대신 AI가
판단) 사본을 만들어 그걸 스케줄하면 됩니다. 사람 게이트를 떼는 건 공짜가 아닙니다 — 그 체크포인트는
안전망이었으니 — 뚫린 구멍 주변의 자동 게이트를 조이세요(애매하면 보수적 분기로, 클린 리뷰 게이트는
엄격하게 유지). 이건 `/odin new`나 수동 복사로 하는 **의식적인 작성 행위**여야 합니다. 스케줄러가
대신 해 주지 않습니다.

## 빠른 시작

`daily-issue-plan`을 매일 아침 09:00에 보드를 채우도록 스케줄합니다.

**1. 등록**(검증한 뒤 데이터로 기록):

```
/odin schedule register daily-issue-plan "0 9 * * *"
```

`register`는 스케줄 가능성을 확인한 뒤, 루프의 **외부 행위**(`git push`, `gh pr create` 같은 것)를
드러내고 무인으로 실행됨을 **확인**받습니다. **명시적 동의**가 있으면 다음을 씁니다:

- `.odin-loop/schedules/daily-issue-plan.yaml` — 스케줄(데이터)
- `.odin-loop/schedules/daily-issue-plan.settings.json` — 무인 실행용 보수적 권한 프로파일
  ([안전 모델](#안전-모델) 참고)

아직 OS는 건드리지 않았습니다.

**2. 설치**(OS 트리거 생성):

```
/odin schedule install daily-issue-plan
```

macOS에선 `~/Library/LaunchAgents/com.odin-loop.hermod.daily-issue-plan.plist`에 LaunchAgent를
쓰고 로드합니다. Linux에선 crontab 항목을 추가합니다. 트리거는 매일 09:00에
`claude -p "/odin run daily-issue-plan" --settings <프로파일>`을 실행합니다.

**3. 확인**(발화 여부 — 실행 로그를 읽음):

```bash
cat .odin-loop/schedules/daily-issue-plan.log
```

매 틱이 한 줄을 남깁니다: 시작, 스케줄 가능성 재검증, 종료 상태(또는 거부/스킵). 09:00에 실행
기록이 보이면 스케줄이 동작하는 것입니다.

## 안전 모델

"사람 게이트 없음"은 안전한 무인 실행의 **필요조건이지 충분조건이 아닙니다** — 모든 게이트가
`ai`인 루프도 파괴적 외부 행위를 할 수 있습니다(PR 머지 루프는 *머지*하고, 빌드 루프는 *ship*).
Hermóðr는 그 틈을 세 겹으로 메웁니다:

- **폭발 반경 확인.** `register` 시 루프의 외부 행위(`git push`, `gh pr create`, `gh pr merge`,
  `gh issue create`, 보드 이동)를 스테이지 프롬프트에서 감지·나열하고, 스케줄을 쓰기 전에 명시적
  동의를 받습니다. `list`가 그 동의된 집합을 계속 보여 줍니다.
- **Scoped settings 프로파일.** 무인 실행은
  `--settings .odin-loop/schedules/<loop>.settings.json`으로 시작합니다 — **절대**
  `--dangerously-skip-permissions`가 아닙니다. 기본 프로파일은 의도적으로 좁습니다:
  `Read`/`Write`/`Edit`/`Glob`/`Grep` + 루프가 실제로 필요로 하는 scoped `Bash(<도구>:*)`(예:
  `Bash(git:*)`, `Bash(gh:*)`)만, `rm`/`sudo`는 거부. 평범한 JSON 파일이라 직접 편집할 수
  있습니다 — 도구가 부족하면 **넓히고**, 더 잠그려면 **좁히세요**.
- **Fire-time 재검증.** 스케줄 가능성을 등록 때만이 아니라 **매 발화마다** 다시 확인합니다. 루프가
  그 사이 사람 게이트나 interview 단계를 얻었다면, 실행하지 않고 **거부하고 로그**에 남깁니다 —
  루프를 멈춤 지점으로 몰지 않습니다.

## 스케줄 관리

cron·설치 상태·동의된 외부 행위와 함께 모든 스케줄을 나열:

```
/odin schedule list
```

하나 제거 — 설치돼 있으면 **OS 트리거를 먼저 언인스톨**한 뒤 선언과 프로파일을 삭제하므로, 제거한
스케줄에 대해 아무것도 계속 발화하지 않습니다:

```
/odin schedule remove daily-issue-plan
```

`uninstall`은 트리거만 내리고 선언은 남깁니다 — 잊지 않고 잠시 멈추고 싶을 때:

```
/odin schedule uninstall daily-issue-plan
```

## 알림

스케줄 실행은 결과를 로그에만 씁니다. 실패를 로그 없이 알아채려면 데스크톱 **알림**을 켜세요.
`register` 시 정책을 정합니다:

```
/odin schedule register daily-issue-plan "0 9 * * *" --notify on-failure
```

- `on-failure`(기본) — 진짜 문제(`error`, 또는 fire-time 재검증 `refused`)에만 알림. 성공·양성 락
  스킵엔 조용.
- `always` — 성공 포함 매 실행 알림.
- `off` — 알림 없음.

알림은 **best-effort**입니다: OS 내장 메커니즘(macOS `osascript`, Linux `notify-send` — 추가 설치
없음)을 쓰고, 활성 GUI 세션이 없으면 표시되지 않을 수 있어 **로그가 진실의 출처**로 남습니다. 알림
실패는 로그에 남고 run 결과를 절대 바꾸지 않습니다.

## launchd vs crontab

`install`은 OS에 따라 백엔드를 고르거나, 강제할 수 있습니다. **macOS**는 LaunchAgent plist를
`~/Library/LaunchAgents/com.odin-loop.hermod.<loop>.plist`에 쓰고(로그아웃/재부팅 생존),
**Linux**는 `crontab` 항목을 추가합니다. 등록 시 `--platform launchd|cron|auto`로 선택을
덮어쓸 수 있습니다.

설치된 트리거를 직접 확인:

```bash
# macOS
cat ~/Library/LaunchAgents/com.odin-loop.hermod.daily-issue-plan.plist
# Linux
crontab -l | grep hermod
```

launchd의 캘린더 형식은 모든 cron 표현식을 표현하진 못합니다(`*/15` 같은 step·range). 그런 경우엔
`--platform cron`으로 등록해 crontab을 쓰세요.

## 명령 레퍼런스

모든 명령은 `/odin schedule <서브커맨드>`이고, 내부적으로 `scripts/hermod.py`를 호출합니다(직접
호출도 가능 — CI/스크립팅에 유용):

| 명령 | 동작 |
| --- | --- |
| `register <loop> "<cron>"` | 스케줄 가능성 검증, 외부 행위 동의, 선언 + 기본 프로파일 작성. **OS 변경 없음.** |
| `install <loop>` | OS 트리거 생성·로드(launchd plist / crontab 항목). |
| `list` | cron·설치 상태·동의된 외부 행위와 함께 스케줄 나열. |
| `uninstall <loop>` | OS 트리거 내림; 선언은 유지. |
| `remove <loop>` | 설치돼 있으면 언인스톨 후 선언 + 프로파일 삭제. |

원시 CLI도 동일합니다 — 예:
`python3 scripts/hermod.py register <loop> --cron "<식>" --project-dir <루트> --ack`,
그리고 `… run <loop>`은 OS 트리거가 호출하는 fire-time 진입점입니다.

스케줄에 필요한 모든 것은 gitignore된 `.odin-loop/schedules/` 아래에 있습니다:

| 파일 | 역할 |
| --- | --- |
| `<loop>.yaml` | 스케줄: `loop`, `cron`, `settings_profile`, `platform`, `project_dir`, `log`, `created_at`, `enabled`, `outward_actions`, `notify` |
| `<loop>.settings.json` | 무인 실행용 scoped 권한 프로파일 |
| `<loop>.log` | 발화당 한 줄(시작, 재검증, 종료 / 거부 / 스킵) |
| `<loop>.lock` | 중복 실행 가드(PID + run id) |

## 문제 해결

- **안 돌았어요.** `.odin-loop/schedules/<loop>.log`를 읽으세요. launchd와 cron은 **최소
  PATH**로 돌아서 `claude`/`gh`/`git`이 해석 가능해야 합니다. 바이너리 누락은 조용한 무동작이 아니라
  시끄러운 실패로 로그에 남습니다.
- **스킵됐어요.** 이전 실행이 아직 `.odin-loop/schedules/<loop>.lock`을 쥐고 있었습니다. 겹친
  발화는 쌓이지 않습니다 — 두 번째는 `skipped`를 로그하고 종료. 크래시된 실행의 스테일 락(죽은
  PID)은 자동 회수됩니다.
- **거부됐어요.** fire-time 재검증이 루프가 더 이상 스케줄 불가임을 발견했습니다(사람
  게이트/interview를 얻음). 로그가 문제 단계를 알려 줍니다 — 루프를 고치거나 autonomous 변종을
  다시 작성하세요.
- **인증 만료.** 헤드리스 실행은 `claude` 로그인을 씁니다. 토큰이 만료되면 실패가 로그에 보입니다.
  재인증하면 다음 틱부터 진행됩니다.

## 더 보기

- [커스텀 루프 작성](authoring-loops.ko.md) — 스케줄할 루프를 직접 쓰기.
- [기능](features.ko.md) — `schedule`을 포함한 모든 `/odin` 명령.
- [설계](design.ko.md) — loop-as-data 모델, 게이트, 노르드 아키텍처.
