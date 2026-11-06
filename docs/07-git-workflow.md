# Git · pull · push · PR 규칙

## 브랜치

| 브랜치 | 용도 | 직접 push |
| --- | --- | --- |
| main | 제출·시연 가능한 버전 | 금지, develop에서 PR |
| develop | 팀 통합 | 금지, 기능 브랜치에서 PR |
| feat/seat-reservation | 기능 | 본인 브랜치만 허용 |
| fix/refund-duplicate | 버그 | 본인 브랜치만 허용 |
| docs/api-contract | 문서 | 본인 브랜치만 허용 |
| chore/ci | 환경·도구 | 본인 브랜치만 허용 |

브랜치는 `type/작업설명` 형식으로 만들고 한 브랜치에서 한 작업만 다룬다.
이슈 작성·번호 사용·PR 연결은 선택 사항이다. 기능 브랜치에서 바로 작업을 시작할 수 있다.
초기 저장소 등록은 관리자가 한 번 수행한다.
아래 명령은 원격 저장소에 `develop` 브랜치가 준비된 뒤 사용한다.
프로젝트 파일 생성만으로 GitHub 저장소나 브랜치 보호가 설정되지는 않는다.

## 작업 시작

작업 중인 변경을 먼저 commit하거나 이름을 붙여 stash한다. 공통 브랜치에 미완성 변경을 섞지 않는다.

~~~powershell
git status
git switch develop
git fetch origin
git pull --ff-only origin develop
git switch -c feat/seat-reservation
~~~

--ff-only가 실패하면 자동 reset하지 말고 로컬 develop의 별도 commit 여부를 확인한다.
팀 브랜치 이력은 rebase하지 않는다. 개인 기능 브랜치도 공유 후에는 merge로 갱신한다.

## 커밋과 push

형식: type(scope): 내용. type은 feat, fix, docs, refactor, test, chore 중 선택한다.
예: feat(reservation): 구간 중복 예약 차단. 본문에는 변경이 필요한 이유를 적는다.
관련 이슈가 있으면 선택적으로 연결할 수 있다.
파일을 명시해 stage하고 git diff --cached로 비밀값·무관한 변경을 확인한다.

~~~powershell
git add app/services/reservation.py tests/test_reservation.py
git diff --cached
git commit -m "feat(reservation): 구간 중복 예약 차단"
git push -u origin feat/seat-reservation
~~~

위 파일은 작업 예시이며 초기 프로젝트에는 없다. 실제 변경한 경로를 사용한다.
push는 기능 브랜치에만 한다. main/develop 강제 push와 다른 팀원 브랜치 덮어쓰기는 금지한다.
공유된 브랜치에서 `push --force`, `push --force-with-lease`, 공개 이력의 rebase를 사용하지 않는다.
push가 거절되면 원격 변경을 fetch하고 내용을 확인한 뒤 merge한다. 강제 push로 해결하지 않는다.

## PR 전 최신 변경 반영

~~~powershell
git fetch origin
git merge origin/develop
git status
~~~

충돌 파일에서 양쪽 의도를 확인해 수정하고 충돌 표시를 제거한다.
검증 후 해당 파일을 git add하고 merge commit을 완료한 다음 기능 브랜치를 push한다.
판단이 어려운 충돌은 해당 코드 담당자와 확인한다. merge를 취소하려면 git merge --abort를 사용한다.

검증은 프로젝트 루트에서 다음 명령으로 실행한다. DB 업무를 구현했다면 해당 MySQL 테스트도 실행한다.

~~~powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m openapi_spec_validator docs/openapi.json
~~~

## PR과 병합

1. 기능 브랜치 → develop으로 PR을 만든다. 이슈 연결은 선택 사항이며 작업 중이면 Draft를 사용한다.
2. 목적·변경·실행한 검증·화면/API 예시·DB 적용 순서를 템플릿에 적는다.
3. 리뷰 요청과 다른 팀원의 승인은 선택 사항이다. 필요한 경우 변경 영역 담당자에게 요청할 수 있다.
4. CI 통과, 최신 develop 반영, 등록된 리뷰 대화 해결 후 작성자가 squash merge할 수 있다.
5. 병합 후 원격 기능 브랜치를 삭제하고 로컬 develop을 pull --ff-only로 갱신한다.
6. 제출 전 develop → main PR에서 통합 시나리오를 확인한다. main 병합 후 v0.1.0 같은 태그를 관리자가 만든다.

PR 제목은 커밋과 같은 `type(scope): 내용` 형식을 사용한다.
예: `feat(reservation): 구간별 좌석 예약 생성`. 관련 이슈가 있으면 본문에 `Closes #12`처럼 선택적으로 연결할 수 있다.
작성 양식은 [PR 템플릿](../.github/pull_request_template.md)을 사용한다.
미완성 작업은 Draft로 열고, 검증하지 않은 항목은 통과했다고 적지 않는다.

리뷰를 요청할 때 참고할 담당자는 DB·무결성 김준휘, 화면 김소연,
회원·운행·검색 김용우, 예약·결제·환불·탑승 김준하다.

병합 후 로컬 기능 브랜치를 정리할 때는 먼저 본인 작업이 원격 `develop`에 포함됐는지 확인한다.
squash merge 뒤에는 `git branch -d`가 거절될 수 있으므로 자동으로 `-D`를 실행하지 않는다.

## GitHub에서 관리자가 설정할 항목

main과 develop 보호 규칙: PR 필수, 대화 해결 필수, CI의 python·frontend 체크 성공 필수,
force push·브랜치 삭제 금지. 리뷰 승인 필수 인원은 0명으로 두고,
코드 소유자 승인·마지막 push 승인·새 commit 시 기존 승인 해제는 사용하지 않는다.
branch protection과 merge 방식 설정은 원격 저장소에서 수동으로 적용해야 한다.
저장소 URL이 제공되지 않아 이 파일 생성 과정에서는 원격 작업을 하지 않았다.

