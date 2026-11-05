# 구조와 FastAPI 사용 방식

## 요청 처리

Jinja2 화면 및 JavaScript → FastAPI router → service → repository → MySQL 순서다.
Pydantic schema는 요청·응답 검증, SQLAlchemy model은 DB 매핑을 맡는다.
Bootstrap은 화면 스타일, Jinja2는 서버 HTML 템플릿에 사용한다.
API URL /api/v1과 FastAPI의 Swagger UI /docs는 서로 다른 용도다.

| 경로 | 책임 |
| --- | --- |
| app/main.py | 앱 생성, 정적 파일, 페이지 등록 |
| app/api/ | 도메인별 HTTP 라우터 및 인증 의존성 |
| app/core/ | 환경설정·인증 공통 코드 |
| app/schemas/ | Pydantic 요청·응답 모델 |
| app/models/ | SQLAlchemy 모델 |
| app/services/ | 업무 검증·상태 전이·트랜잭션 |
| app/repositories/ | SQL과 잠금 조회 |
| app/db/ | engine·Session 의존성 |
| app/templates/, app/static/ | HTML·CSS·JavaScript |
| db/ | 순서가 있는 DDL·시연 데이터 |
| tests/ | 기능·통합·동시성 검증 |

동기 SQLAlchemy와 PyMySQL을 사용한다. DB를 호출하는 엔드포인트는 일반 def로 작성한다.
async def에서 동기 DB 호출로 이벤트 루프를 막지 않는다. async DB 전환은 별도 PR로 처리한다.
request당 Session 하나를 주입하고 서비스가 트랜잭션을 소유한다.
예외 발생 시 rollback, 요청 종료 시 close한다. repository는 commit하지 않는다.
지금의 get_db는 세션 공급만 구현하며 업무 서비스와 ORM 모델은 아직 없다.

인증 구현 제안: 짧은 수명의 Bearer JWT를 사용하고 비밀번호는 Argon2로 해시한다.
토큰은 sub=회원 ID, token_version, 만료시간을 담고 요청마다 DB 버전을 확인한다.
로그아웃은 회원 token_version을 증가시켜 해당 회원의 모든 기존 토큰을 무효화한다.
새로고침 토큰은 MVP에서 생략하고 만료 후 재로그인한다. 추가 라이브러리는 인증 PR에서 도입한다.
브라우저는 access token을 메모리에 보관하며 URL·로그·localStorage에 저장하지 않는다.
동일 origin으로 화면과 API를 제공한다. CORS 전체 허용을 기본값으로 두지 않는다.

