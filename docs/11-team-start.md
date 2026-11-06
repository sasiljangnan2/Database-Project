# 팀원 작업 시작 안내

## 지금 사용할 수 있는 공통 기반

- MySQL DDL 16개 테이블과 개별 SQLAlchemy 모델, Base.metadata 등록.
- 회원가입·로그인·전체 로그아웃·본인 조회·정보 수정·비밀번호 변경 API 6개.
- Argon2 해시, HS256 JWT, 매 요청의 token_version·권한·활성 여부 확인.
- `CurrentUser`, `AdminUser`, `DbSession` 의존성과 공통 오류 응답.
- 회원·운행·예약 영역별 요청·응답 모델과 등록된 기능별 라우터.
- 공통 HTML 템플릿, JavaScript API 클라이언트, 11개 계약 샘플, 개발용 미리보기.

운행 검색·좌석 조회·예약·결제·환불·탑승의 실제 업무 API는 아직 구현하지 않았다.
빈 라우터를 가짜 성공 응답으로 채우지 않는다. 현재 `/docs`에는 구현한 API만 표시된다.
이번 작업은 파일 구성과 로컬 검증이며 Render 배포·원격 push·팀원 연락은 수행하지 않았다.

## 각자 처음 실행하기

GitHub 저장소의 공통 기준 버전을 clone하고 **각자 clone한 프로젝트 루트**에서 실행한다.
Windows PowerShell 기준이며 Python 3.11 이상, DB 작업자는 Docker Desktop이 필요하다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[dev]"
.\.venv\Scripts\python.exe scripts/setup_local.py
docker compose up -d db
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`setup_local.py`는 개인 JWT 비밀키가 들어 있는 `.env`를 최초 한 번 생성하고 기존 파일은 보존한다.
생성된 비밀키는 출력하지 않는다. `.env`는 Git에 올리지 않는다.
DB 담당은 먼저 신규 MySQL에서 DDL·seed 적용을 확인하고, 기준 버전을 팀원에게 안내한다.
각자 로컬 DB를 사용하고 Render DB는 추후 통합·시연 환경으로 사용한다.
프론트는 Docker DB를 실행하지 않아도 서버와 `/dev/preview`를 사용할 수 있다.

| 주소 | 목적 |
| --- | --- |
| `/` | 현재 구현 범위와 공통 메뉴 |
| `/docs` | 실제 구현 API 확인·호출 |
| `/dev/preview` | DB 없는 프론트 미리보기, 로컬 설정에서만 활성화 |
| `/api/v1/health` | 프로세스 생존 확인, DB 검사 아님 |

## 파일 담당과 첫 작업

| 담당 | 우선 작업 파일 | 처음 완료할 작업 |
| --- | --- | --- |
| 김준휘 | `db/`, `app/models/`, `tests/test_database_constraints.py` | 실제 MySQL에서 DDL·ORM·초기 데이터 검증, 공통 모델 기준 관리 |
| 김용우 | `app/api/endpoints/auth.py`, `users.py`, `catalog.py`, `runs.py`, `admin_catalog.py`; `app/services/auth.py`; `app/schemas/auth.py`, `catalog.py` | 제공된 회원 API 확인 후 역·열차종류 조회와 직통 운행 검색 구현 |
| 김준하 | `app/api/endpoints/reservations.py`, `tickets.py`, `refunds.py`, `admin_operations.py`; `app/schemas/booking.py` | 회원 의존성을 재사용해 예약·구간 점유 생성과 만료 해제 구현 |
| 김소연 | `app/templates/`, `app/static/` | 공통 base.html과 샘플을 재사용해 검색·좌석·예약 내역 화면 구현 |

`app/main.py`, `app/api/router.py`, `app/core/`, `app/db/`, `pyproject.toml`은 공통 영역이다.
초기에는 김준휘가 공통 변경을 취합한다. 필요한 경우 관련 담당자에게 리뷰를 요청할 수 있으며, 인증 영역은 김용우가 담당한다.
각 라우터는 이미 연결돼 있으므로 기존 파일에 엔드포인트를 추가할 때 중앙 router.py를 수정할 필요가 없다.
ORM 모델을 담당자별로 복제하지 않는다. 공통 모델 변경은 DB 담당자와 합의한 PR로 적용한다.

## 백엔드에서 인증 재사용하기

```python
from app.api.dependencies import CurrentUser, DbSession
from app.models import Reservation
from app.schemas.common import Page

# 본인 대상 조회는 CurrentUser.id를 조건에 넣는다.
# 관리자 작업은 CurrentUser 대신 AdminUser를 받는다.
# 요청 본문에 user_id나 role을 추가하지 않는다.
```

`Principal`은 인증한 사용자 정보다. JWT에 들어 있는 역할을 신뢰하지 않고 DB의 현재 역할을 사용한다.
로그아웃과 비밀번호 변경은 해당 회원의 모든 기존 토큰을 무효화한다.
인증을 우회하는 개발용 토큰이나 실제 앱의 가짜 회원 주입 기능은 제공하지 않는다.
테스트에서만 `dependency_overrides`를 사용하고 제품 코드에 반영하지 않는다.

처음 확인할 때 `/docs`에서 회원가입 → 로그인 순서로 호출하고,
로그인 응답의 access_token을 Authorize에 입력한 뒤 `/users/me`를 호출한다.
로그아웃 뒤 같은 토큰을 재사용하면 401이 반환되는지 확인한다.

예약 서비스는 [업무 규칙](05-business-rules.md)에 따라 열차 행을 잠그고
예약·승차권·모든 단위 구간 점유를 한 트랜잭션으로 저장한다.
예약 담당자는 회원 구현을 새로 만들 필요 없이 위 의존성과 모델을 바로 사용할 수 있다.

## 프론트에서 먼저 작업하기

[sample-catalog.json](sample-catalog.json)은 각 샘플이 어떤 API 응답에 대응하는지 나타낸다.
샘플은 독립적인 가상 시점이며 DB에 저장되지 않는다.

```javascript
import { api, loadSample } from "/static/js/api-client.js";

// 화면 개발 중: 백엔드 업무 구현 없이 사용
const results = await loadSample("runs");
const seats = await loadSample("seats"); // 좌석 응답은 페이지 객체가 아닌 배열

// 실제 API가 구현된 뒤 연결
// const results = await api.request("/runs?departure_station_id=1&arrival_station_id=3&departure_date=2026-12-01&passenger_count=1");
```

로그인 화면을 구현하면 `api.request('/auth/login', {method: 'POST', body: ...})`의
`access_token`을 `api.setAccessToken()`에 전달한다. 이 값은 메모리에만 보관한다.
401 응답은 토큰을 지우므로 재로그인 안내를 표시한다.
`APIError.code`, message, details로 실패 화면을 만든다. 서버 내부 오류 문자열을 화면에 그대로 표시하지 않는다.
템플릿은 `base.html`을 extends하고 페이지별 JavaScript 파일을 추가한다.

## API와 DB 변경 합의

1. 기능 작업 전에 [API 명세](04-api.md)의 해당 요청·응답·실패 조건을 확인한다.
2. 변경이 필요하면 프론트와 해당 백엔드 담당자가 먼저 합의한다.
3. `docs/openapi.json`, 공통 Pydantic 모델, 샘플 JSON, 구현·테스트를 같은 PR에서 맞춘다.
4. 테이블 변경은 공통 ORM과 후속 마이그레이션 SQL을 함께 변경한다. 기존 seed만 고쳐 공유 DB가 바뀐다고 가정하지 않는다.

## 매일 합치는 방법

기능 브랜치에서 작은 작업 단위로 PR을 보내고 `develop`에서 통합한다.
이슈 작성과 PR 연결은 선택 사항이며 기능 브랜치에서 바로 작업을 시작할 수 있다.
각 기능 전체를 끝낸 뒤 한 번에 합치기보다 스키마·조회·화면 연결처럼 검증 가능한 단위로 합친다.
기준 API·공통 모델 변경 PR을 먼저 합치고, 담당자들은 최신 `develop`을 반영한다.
실제 브랜치 보호 설정은 저장소 관리자가 [Git 규칙](07-git-workflow.md)에 따라 적용한다.

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m openapi_spec_validator docs/openapi.json
node --test tests/frontend.test.mjs
```

Node 테스트는 Node.js 22 이상 기준이며 프론트 클라이언트의 토큰·오류 처리를 검증한다.
MySQL 검사는 TEST_DATABASE_URL이 없으면 건너뛴다. [테스트 계획](08-test-plan.md)의 빈 전용 DB를 사용한다.
회원 HTTP 단위 테스트의 SQLite users 테이블은 MySQL의 FK·잠금·구간 점유 검증을 대체하지 않는다.

## 개발 관리자 계정

일반 회원가입 API는 MEMBER만 생성한다. 관리 화면을 개발할 때 담당자가 로컬 DB에서 명시적으로 실행한다.

```powershell
.\.venv\Scripts\python.exe scripts/create_admin.py --email admin@example.com --name "개발 관리자"
```

비밀번호는 터미널에서 숨김 입력하며 인자로 받지 않는다. 기존 회원을 자동 승격하지 않는다.
