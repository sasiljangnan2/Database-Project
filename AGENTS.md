# 프로젝트 작업 규칙

- Python, FastAPI, MySQL, Jinja2, Bootstrap을 사용한다.
- 먼저 README.md, docs/10-decisions.md, docs/11-team-start.md를 읽는다.
- 공통 ORM·Pydantic 모델·인증 의존성을 재사용한다. 모델을 각 담당 영역에 복제하지 않는다.
- 샘플 JSON은 가상 응답이며 실제 업무 구현으로 간주하지 않는다.
- DB는 docs/sources/ERD-reference.png의 16개 엔터티를 기준으로 하며 구현용 추가 필드는 docs/03-database.md에 구분한다.
- docs/openapi.json은 예정 계약이며 실제 구현 상태와 구별한다.
- 업무 규칙 변경 시 요구사항, API, DB 및 테스트 문서를 함께 갱신한다.
- 구간 중복 방지는 조회 후 저장만으로 구현하지 않는다. 문서의 잠금 규칙을 따른다.
- 좌석점유의 복합 PK와 모든 구간 INSERT를 예약 트랜잭션에 포함한다. 취소·만료 시 점유를 함께 해제한다.
- 기존 SQL을 수정해 공유 DB가 자동 변경된다고 가정하지 않는다.
- 시연용 결제만 구현하며 실제 카드정보와 결제대행사는 연결하지 않는다.
- 원격 push, PR 생성, 팀원 메시지 전송은 사용자가 요청한 경우에만 수행한다.

