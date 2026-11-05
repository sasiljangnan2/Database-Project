# 기차 예약 및 승차권 관리 시스템

데이터베이스설계 7분반 2팀. Python · FastAPI · Jinja2 · Bootstrap · MySQL.

## 현재 제공 범위

제공된 제안서와 업무분석서를 바탕으로 구성한 **팀 개발 시작용 프로젝트**다.
서버 프레임워크는 **FastAPI**로 통일했다. 먼저 [시스템 설계서](docs/설계서.md)를 읽는다.

| 구분 | 제공 내용 |
| --- | --- |
| 실행 코드 | FastAPI 앱, Jinja2 홈 화면, 정적 CSS, `GET /api/v1/health`, DB 세션 설정 |
| DB 파일 | MySQL 14개 테이블 초기 DDL, 가상 기준정보·운행·운임 데이터, Docker Compose |
| 개발 문서 | 요구사항, 설계서·ERD, API 계약, 업무·개발 규칙, 테스트 계획, 역할·작업 순서 |
| 협업 파일 | pull·push·PR 규칙, PR·이슈 템플릿, GitHub Actions CI, Git 제외 규칙 |

회원·검색·예약·결제 등 업무 API는 설계 명세이며 아직 구현하지 않았다.
SQL은 MySQL에서 실제 실행 검증 전이므로 개발 DB에서 먼저 확인한다.

## 시작

Python 3.11 이상이 필요하다. PowerShell에서 아래 명령을 실행한다.
홈 화면과 프로세스 상태 확인은 DB 없이 실행할 수 있다.

~~~powershell
Set-Location -LiteralPath 'C:\Users\jack4\Desktop\일\깃\데베설'
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
~~~

로컬 주소: http://127.0.0.1:8000, 실행 중인 API 문서: http://127.0.0.1:8000/docs.
홈 화면은 Bootstrap CDN을 사용하므로 해당 스타일에는 인터넷 연결이 필요하다.
전체 예정 API 계약은 docs/openapi.json을 Swagger Editor 등에 불러와 확인한다.
앱의 /docs에는 실제 구현된 API만 표시된다.

`py` 명령이 없으면 Python 3.11 이상을 설치하거나 사용 중인 Python 실행 경로로 대체한다.
환경파일을 이미 작성했다면 복사 명령은 생략한다. 서버 종료는 실행한 터미널에서 Ctrl+C다.

## 개발 DB 실행

Docker Desktop의 Compose를 사용한다. 별도 터미널에서 프로젝트 루트로 이동해 실행한다.
직접 설치한 MySQL을 사용한다면 8.0.16 이상에서 SQL을 순서대로 적용하고 `.env`를 맞춘다.

~~~powershell
docker compose up -d db
docker compose ps
~~~

DB는 첫 볼륨 생성 시 db/001_schema.sql, db/002_seed.sql을 순서대로 적용한다.
기존 볼륨에서는 초기 SQL이 다시 실행되지 않는다. 데이터를 지우는 down -v 대신
변경 SQL을 새 마이그레이션으로 작성해 검토 후 적용한다.
DB 직접 연결: localhost:3307 / train_app / train_app / train_local_pw.
이는 로컬 개발 전용 값이며 외부 배포 시 별도 계정과 비밀값을 사용한다.

## 검증

~~~powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m openapi_spec_validator docs/openapi.json
~~~

## 문서

| 파일 | 내용 |
| --- | --- |
| [docs/설계서.md](docs/설계서.md) | FastAPI 기준 기술 스택, 시스템 구성·주요 처리 설계 |
| [docs/01-requirements.md](docs/01-requirements.md) | 범위, 요구사항, 팀원 역할 |
| [docs/02-architecture.md](docs/02-architecture.md) | 폴더 구조, FastAPI 개발 방식 |
| [docs/03-database.md](docs/03-database.md) | 14개 테이블, 제약, 잠금 처리 |
| [docs/ERD.mmd](docs/ERD.mmd) | 14개 테이블 관계를 나타낸 Mermaid ERD |
| [docs/04-api.md](docs/04-api.md) | 요청·응답·권한·오류 계약 |
| [docs/openapi.json](docs/openapi.json) | 전체 예정 API OpenAPI 3.1 계약 |
| [docs/05-business-rules.md](docs/05-business-rules.md) | 구간 중복, 상태 전이, 결제·환불 |
| [docs/06-development.md](docs/06-development.md) | 코딩, DB 변경, 보안 규칙 |
| [docs/07-git-workflow.md](docs/07-git-workflow.md) | branch, commit, pull, push, PR |
| [docs/08-test-plan.md](docs/08-test-plan.md) | 기능·권한·동시성 검증 |
| [docs/09-roadmap.md](docs/09-roadmap.md) | 작업 순서 및 완료 기준 |
| [docs/10-decisions.md](docs/10-decisions.md) | 출처, 원문과 추가 설계의 구분 |
| [docs/sources/README.md](docs/sources/README.md) | 제공된 두 문서의 링크와 텍스트 사본 안내 |
| [docs/verification.json](docs/verification.json) | 이번 파일 구성·실행 검증 결과와 미검증 항목 |

## 팀 작업 시작

1. `docs/01-requirements.md`에서 담당 기능과 완료 기준을 확인한다.
2. `docs/04-api.md`와 `docs/openapi.json`으로 요청·응답을 맞춘다.
3. `docs/06-development.md`와 `docs/07-git-workflow.md`에 따라 기능 브랜치에서 작업한다.
4. 테스트 후 PR 템플릿에 변경 내용·결과·DB 적용 순서를 작성하고 다른 팀원의 리뷰를 받는다.

GitHub의 branch protection과 리뷰 강제는 문서만으로 적용되지 않는다.
저장소 관리자가 docs/07-git-workflow.md에 따라 설정해야 한다.
이 프로젝트는 원격 저장소 연결·commit·push를 자동 수행하지 않는다.

