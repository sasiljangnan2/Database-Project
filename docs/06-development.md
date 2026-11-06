# 개발 규칙

## 코드

- 파일·함수·변수 snake_case, 클래스 PascalCase, 상수 UPPER_SNAKE_CASE.
- Python 4칸, UTF-8, 타입힌트, Ruff 100자 기준을 사용한다.
- 라우터는 HTTP 변환, 서비스는 업무, repository는 SQL을 담당한다.
- 좌석점유는 서비스가 계산해 예약·승차권과 같은 트랜잭션에 저장한다. 점유 PK 충돌은 전체 rollback한다.
- 취소·만료 시 해당 ticket_id의 점유만 해제한다. 환불 결과와 점유 해제를 별개 상태로 처리한다.
- request 모델은 extra=forbid를 기본으로 하며 role·금액·user_id 등 서버 결정값을 받지 않는다.
- 비밀번호 해시·토큰·DB 접속문자열은 응답과 로그에 포함하지 않는다.
- DB 시간·현재시간은 공통 UTC 함수를 거치게 하여 기한 경계 테스트가 가능해야 한다.
- 예외를 모두 200으로 감싸지 않는다. 공통 error 형식과 적절한 상태코드를 사용한다.
- 공통 RequestValidationError 핸들러가 422를 error 형식으로 바꾼다. 입력 원문이나 ctx를 오류 응답에 추가하지 않는다.

## API 변경

이슈에서 요청·응답 예시와 실패 조건을 합의한 뒤 docs/openapi.json, docs/04-api.md,
Pydantic schema, 구현을 같은 PR에서 변경한다. 임의 URL·상태값을 프론트에서 먼저 만들지 않는다.
구현 완료 시 실제 app.openapi()와 예정 계약의 해당 경로를 비교한다.

## DB 변경

001_schema.sql은 신규 초기화용이다. 팀이 사용하기 시작한 후에는 후속 번호 SQL을 작성한다.
DDL 자동 commit에 주의하며 되돌리기는 별도 SQL/복구 절차로 문서화한다.
첨부 ERD를 반영한 기존 14개 테이블 DB의 변경안은 [마이그레이션 안내](../db/migrations/README.md)를 따른다.
개발 DB 백업, 새 DB 적용, 기존 DB 업그레이드 순서로 검증한다.
공유 DB에서 DROP, TRUNCATE, 볼륨 삭제는 별도 합의 없이 실행하지 않는다.
예약·결제·환불 관련 변경은 DB·API·업무 규칙과 테스트를 함께 맞춘다.
필요하면 DB 담당자나 해당 서비스 담당자에게 리뷰를 요청할 수 있다.

## 환경

.env는 개인 로컬 값이며 Git에 올리지 않는다. 새 설정은 .env.example에 빈값/개발용 예시로 추가한다.
패키지를 추가하면 pyproject.toml을 갱신한다. 의존성은 pyproject.toml에 선언하고,
검증 환경에서 고정한 constraints.txt를 설치 시 함께 사용한다. CI도 같은 constraints를 적용한다.
constraints는 전체 OS 공통 lock이 아니며 OS별 추가 의존성은 각 환경에서 해석한다. 팀 기준 Python은 3.12다.
관리자 가입 API는 제공하지 않는다. 개발 전용 계정 생성 스크립트에서 해시를 만들고 별도 운영 권한으로 지정한다.

