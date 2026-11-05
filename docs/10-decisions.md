# 출처 및 설계 결정

## 원문

- 기준 제안서: https://docs.google.com/document/d/1eDCdw0_zxvUQLHEWRPFBUaleSqtQ9oj-/edit
- 업무 규칙 참고: https://docs.google.com/document/d/1lst6UsPt1-7TQZISew9ixknkWA5f3ZE3m_V1OhgDxf0/edit
- 2026-11-06에 두 링크의 본문을 확인했다. 첫 문서는 Word 파일, 두 번째 문서는 텍스트 파일로 제공된다.
- 확인한 제안서에는 이미 Python / FastAPI / Jinja2 / Bootstrap / MySQL이 명시되어 있다.
- 사용자 요청에 따라 프로젝트의 [시스템 설계서](설계서.md)와 기술 스택을 FastAPI 기준으로 통일했다.
- 원문 텍스트와 출처 정보는 [sources/README.md](sources/README.md)에 보관한다. 원본 Drive 파일의 내용은 변경하지 않았다.

## 원문 요구와 추가 제안

14개 데이터, 팀원 역할, 직통 검색, 여러 좌석 예약, 시연용 결제, 승차권별 환불과 탑승 확인은 원문 기준이다.
아래 세부값은 실행 가능한 개발 계약을 위해 추가한 초안이며 과제 원문이 확정한 정책으로 인용하지 않는다.

| 항목 | 초기 제안 |
| --- | --- |
| 예약 기한 | 생성 후 10분, 승차역 출발 전까지만 |
| 예약 인원 | 요청당 1~9명 |
| 환불 | 출발 전·탑승 확인 전 전액, 수수료 없음 |
| 인증 | Bearer JWT + 사용자 token_version, 로그아웃 시 전 기기 무효화 |
| 화면 | Jinja2 + Bootstrap, 동일 서버 제공 |
| 동시성 | 열차 부모 행 잠금으로 동일 열차 작업 직렬화 |
| 시간 | DB UTC, API ISO 8601, 검색일 Asia/Seoul |
| 금액 | 원 단위 정수, 서버 계산 |
| Git | main/develop + 기능 브랜치, PR 승인 1명·CI 필수 |

FastAPI는 라우팅·요청 검증·OpenAPI 생성에 사용하고 Jinja2는 HTML 렌더링을 맡는다.
SQLAlchemy/PyMySQL은 DB 연결 계층이며 원문의 MySQL을 변경하지 않는다.
현재 앱에는 업무 기능·인증·ORM·예약 정리 작업이 구현되지 않았다.
예정 계약과 초기 SQL은 개발을 시작할 때 검증·보완할 대상이다.

