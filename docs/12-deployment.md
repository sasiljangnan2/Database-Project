# Docker 실행과 Render 배포

FastAPI가 HTML·정적 파일·API를 함께 제공한다. 웹 이미지에는 Python 3.12와 앱 실행 의존성을 넣고,
MySQL 접속정보와 JWT 비밀키는 실행할 때 환경변수로 전달한다.

## 로컬에서 웹과 MySQL 실행

Docker Desktop을 Linux 컨테이너 모드로 실행한 뒤 프로젝트 루트에서 실행한다.
`setup_local.py`는 Python 표준 라이브러리만 사용하며 기존 `.env`를 보존한다.

```powershell
py -3.12 scripts/setup_local.py
docker compose --profile web up --build -d
docker compose --profile web logs -f web
```

- 홈페이지: http://127.0.0.1:8000/
- 실제 구현 API 문서: http://127.0.0.1:8000/docs
- 개발 미리보기: http://127.0.0.1:8000/dev/preview (`ENABLE_FRONTEND_PREVIEW=true`일 때)

Compose의 `web` 서비스는 `db:3306`으로 MySQL에 연결하고 DB의 TCP 준비 상태를 기다린다.
호스트 PC에서 DB에 직접 연결할 때는 기존 `127.0.0.1:3307`을 사용한다.
웹 설정은 루트 `.env`의 APP_NAME·JWT_SECRET_KEY·ACCESS_TOKEN_EXPIRE_MINUTES·ENABLE_FRONTEND_PREVIEW를 읽는다.
Compose의 DB 접속정보는 로컬 개발용 값이다.

첫 DB 볼륨 생성 시 `db/001_schema.sql` → `db/002_seed.sql`을 적용한다.
기존 볼륨의 스키마 변경은 [마이그레이션 안내](../db/migrations/README.md)를 따른다.
DB만 사용하려면 기존처럼 `docker compose up -d db`를 실행한다.

로그 보기는 Ctrl+C로 끝내고, 서비스는 아래 명령으로 중지한다. DB 볼륨은 유지된다.

```powershell
docker compose --profile web stop
```

## 웹 이미지만 실행

홈·상태 확인·API 문서는 DB 연결 없이 열 수 있다. 회원 API는 준비된 MySQL과 JWT 비밀키가 필요하다.

```powershell
docker build -t train-web .
docker run --rm -p 127.0.0.1:8000:8000 train-web
```

DB와 인증을 사용할 때는 접속 가능한 MySQL의 `DATABASE_URL`과 `JWT_SECRET_KEY`를
`docker run --env-file` 또는 실행 환경의 비밀 설정으로 전달한다.
독립 실행 컨테이너의 `127.0.0.1`은 해당 컨테이너이므로 DB 주소는 연결 환경에 맞게 지정한다.

기본 웹 포트는 8000이다. `PORT`를 전달하면 해당 포트에서 실행한다.
예를 들어 `docker run --rm -e PORT=8080 -p 127.0.0.1:8000:8080 train-web`로 실행할 수 있다.

## Render에 배포

Dockerfile이 포함된 PR을 `develop`에 반영한 뒤 Render에서 New → Web Service를 선택하고
GitHub의 `sasiljangnan2/Database-Project` 저장소를 연결한다.

| 설정 | 값 |
| --- | --- |
| Branch | develop (팀 개발 서버 기준) |
| Language | Docker |
| Root Directory | 비워두기 |
| Dockerfile Path | ./Dockerfile |
| Docker Command | 비워두기: 이미지의 CMD 사용 |
| Health Check Path | /api/v1/health |

Python 버전과 패키지 설치는 Dockerfile에서 정한다. Render의 `PORT` 값으로 Uvicorn을 실행하고,
`exec`를 사용해 종료 신호를 앱에 전달한다.
Render는 저장소의 Dockerfile로 웹 이미지를 빌드한다. 로컬 Compose 파일은 개발 환경 실행에 사용한다.

Environment에는 다음 값을 설정한다.

| 변수 | 값 |
| --- | --- |
| JWT_SECRET_KEY | 최소 32바이트의 무작위 비밀키 |
| DATABASE_URL | 접속 가능한 MySQL 주소, 아래 형식 참고 |
| ENABLE_FRONTEND_PREVIEW | false |

```text
mysql+pymysql://DB_USER:DB_PASSWORD_URLENCODED@DB_HOST:3306/DB_NAME?charset=utf8mb4
```

비밀번호의 `@`, `:`, `/`, `#` 같은 문자는 URL 인코딩한다.
환경변수 값은 Render의 서비스 설정에 저장한다.
비밀키가 필요하면 로컬에서 아래 명령으로 생성해 Render의 JWT_SECRET_KEY에 입력한다.

```powershell
py -3.12 -c "import secrets; print(secrets.token_urlsafe(48))"
```

처음 준비한 빈 MySQL에는 `db/001_schema.sql` → `db/002_seed.sql` 순서로 수동 적용한다.
기존 DB의 변경은 [마이그레이션 안내](../db/migrations/README.md)를 따른다.
Render 웹 서비스를 배포하면 홈페이지와 `/docs`를 확인하고, MySQL 연결·초기화 후 회원 API를 확인한다.
현재 검색·예약·결제·환불·탑승 업무 API는 팀원별 구현 대상이다.

## 컨테이너 검증 범위

CI의 `docker` 작업은 Compose 설정과 실제 이미지 빌드를 확인하고,
비밀 환경파일 제외·일반 사용자 실행·사용자 지정 PORT·홈·API 문서·정적 JS 응답을 검증한다.
`/api/v1/health`는 웹 프로세스의 응답 확인이다. MySQL 제약·ORM 검사는 별도 `python` CI가 수행한다.
운영 DB와 실제 Render 배포의 연결 상태는 해당 환경에서 확인한다.

## 참고

- [Render Docker 배포](https://render.com/docs/docker)
- [Dockerfile 명령](https://docs.docker.com/reference/dockerfile/)
- [Docker Compose 프로필](https://docs.docker.com/compose/how-tos/profiles/)
