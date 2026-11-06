# DB 설계 — 첨부 ERD 기준

[사용자 제공 ERD](sources/ERD-reference.png)를 DB 구조의 기준으로 삼는다.
기존 제안서의 14개 데이터에 **열차종류와 좌석점유**를 반영해 **16개 테이블**로 구성했다.
`db/001_schema.sql`은 MySQL 8.0.16 이상용 신규 초기화 DDL이다.
실행용 관계도는 [ERD.mmd](ERD.mmd), 기존 DB 변경 절차는 [마이그레이션 안내](../db/migrations/README.md)를 따른다.
ORM 16개와 회원·인증 서비스를 구현했다. 예약 등 다른 업무와 실제 MySQL 실행 검증은 남아 있다.

## 테이블 대응

| 첨부 ERD | 테이블 | 핵심 제약 및 연결 |
| --- | --- | --- |
| 열차종류 | train_types | code PK = 열차종류코드, name = 종류명 |
| 열차 | trains | identifier UNIQUE, train_type_code FK → train_types.code |
| 노선 | routes | id, name; 운행방향은 이 테이블에 두지 않음 |
| 역 | stations | id, name; region은 선택 메타데이터 |
| 운행 | runs | 열차·노선 FK, service_number, service_date, status, direction |
| 노선정차역 | route_stops | 노선·역 FK, UNIQUE(route_id, stop_order) |
| 구간운임 | fares | 출발·도착역 FK, train_type_code FK, 좌석등급·운임 |
| 회원 | users | email UNIQUE, password_hash, 이름·연락처 |
| 좌석 | seats | 열차 FK, UNIQUE(train_id, carriage_no, seat_number) |
| 운행정차일정 | run_stops | 운행·노선정차역 FK, 도착·출발 예정일시 |
| 예약 | reservations | 회원 FK, 예약일시·상태, 운영용 운행·기한·총액 |
| 승차권 | tickets | 예약·좌석·승하차 운행정차·운임 FK, 발권일시·상태 |
| 결제 | payments | 예약 FK, 금액·수단·상태·일시, 예약당 성공 1건 |
| 좌석점유 | seat_occupancies | PK(run_id, seat_id, segment_start_order), ticket_id FK |
| 탑승확인 | boarding_checks | ticket_id UNIQUE FK, checked_at |
| 환불 | refunds | 결제·승차권 FK, 금액·상태·처리일시, 승차권당 1건 |

## 첨부 그림과 물리 구현의 차이

그림의 엔터티와 핵심 관계를 유지하며 다음 항목은 업무 구현에 필요한 보완으로 구분한다.

- 그림의 비밀번호는 실제로 `password_hash`에 해시로 저장한다.
- 회원의 role·token_version·is_active·created_at과 기준정보의 is_active는 권한·이력 관리를 위한 필드다.
- `stations.region`은 그림 밖의 선택 정보다. NULL을 허용하며 역 등록에 필수로 요구하지 않는다.
- `reservations.run_id`, expires_at, total_amount는 한 예약의 운행·결제기한·합계 관리를 위한 필드다.
- `tickets.confirmed_amount`, cancelled_at은 운임 변경 전 금액 보존과 취소 이력에 사용한다.
- 결제의 idempotency_key·request_hash·successful_reservation_id는 중복 결제 방지용이다.
- 환불의 reason·created_at과 탑승 확인의 checked_by는 사유·담당자 이력용이다.
- `run_stops.stop_order`는 실제 운행 진행 순서의 스냅샷이다. 좌석점유의 구간 번호도 이를 따른다.
- 좌석점유의 `(run_id, segment_start_order)`는 `run_stops(run_id, stop_order)`를 추가 FK로 참조한다.

## 운행방향과 순서

방향은 그림처럼 **runs.direction**에 저장한다. 예시는 `A_TO_C`, `C_TO_A`다.
노선정차역의 순서는 노선의 기준 순서이고, 운행정차일정의 순서는 해당 운행의 실제 진행 순서다.
역방향 운행도 `run_stops.stop_order`를 1부터 연속으로 부여한다.
방향 문자열만 바꾸어 시간표를 자동 역순으로 바꾸지 않는다.
운행이 있는 노선의 정차 구성과 예약이 있는 운행의 방향·시간표는 임의 변경할 수 없다.

## 좌석점유와 중복 방지

승차권의 승차 순서 b, 하차 순서 a라면 **b, b+1, …, a-1**의 점유 행을 모두 만든다.
각 행은 `[k, k+1)` 구간 하나를 나타낸다.

| 승차권 구간 | 생성하는 segment_start_order | 결과 |
| --- | --- | --- |
| A(1) → B(2) | 1 | 첫 구간 점유 |
| B(2) → C(3) | 2 | 같은 좌석에 연속 판매 가능 |
| A(1) → C(3) | 1, 2 | 두 구간을 모두 확보해야 성공 |

복합 PK는 같은 운행·좌석·구간에 소유자를 두 개 만들 수 없게 한다.
서비스는 예약·승차권 생성과 **모든 구간의 점유 INSERT**를 한 트랜잭션으로 처리한다.
하나라도 중복이면 전체 rollback하고 `409 SEAT_CONFLICT`를 반환한다.
`INSERT IGNORE`, `REPLACE`, 충돌 소유자를 바꾸는 upsert로 실패를 숨기지 않는다.
입력으로 받은 구간 번호나 ticket_id를 신뢰하지 않고 서비스가 운행정차 일정에서 계산한다.
클라이언트용 좌석점유 생성·삭제 API는 제공하지 않는다.

HELD 중 기한이 남은 승차권과 ISSUED·BOARDED는 점유를 유지한다.
결제 성공은 점유 행을 새로 만들지 않는다. 취소·만료는 해당 승차권의 점유를 삭제하고 상태를 함께 변경한다.
환불 실패 여부는 점유 해제 결과에 영향을 주지 않는다. 예약·승차권·결제 이력은 삭제하지 않는다.
만료 HELD의 물리 점유가 남아 있으면 검색은 이를 제외하고, 쓰기는 잠금 후 만료·점유 삭제를 먼저 확정한다.

## 잠금과 서비스 검증

동일 열차의 작업은 기존처럼 `trains` 부모 행을 `SELECT ... FOR UPDATE`로 잠가 직렬화한다.
예약·취소·결제·만료·운행취소·운행편성이 모두 이 규칙에 참여한다.
잠금 순서는 train → run → reservation → ticket(ID 오름차순) → payment → refund다.
좌석점유 쓰기는 해당 ticket 잠금 아래에서 `(seat_id, segment_start_order)` 오름차순으로 수행한다.
여러 열차는 ID 오름차순으로 잠근다. 잠금 후 재조회하며 deadlock은 전체 rollback 후 최대 2회 재시도한다.

PK는 **삽입된 단위 구간**의 중복을 보장한다. 다음 항목은 여전히 서비스가 검증해야 한다.

- 모든 요청 구간의 점유 행이 누락 없이 생성되는가.
- 좌석점유의 ticket_id가 같은 운행·좌석·승하차 구간의 승차권인가.
- 승하차 일정이 같은 운행이고 승차 < 하차이며 마지막 정차 이후 구간을 만들지 않는가.
- 좌석이 운행에 배정된 열차 소속이고 운임의 열차종류코드·역·등급 조건이 일치하는가.
- 합계·인원·유효기한·상태가 맞고 동일 열차의 운행 시간이 겹치지 않는가.

## 공통 저장 규칙

- 금액은 KRW 정수 BIGINT이며 합계는 서버에서 계산한다.
- DATETIME(6)은 UTC 저장, API는 시간대 포함 ISO 8601을 사용한다.
- service_date는 편성 시작일, 검색 departure_date는 Asia/Seoul 기준 승차역 출발일이다.
- 운임 변경 후에도 tickets.confirmed_amount와 reservations.total_amount는 유지한다.
- FK는 RESTRICT가 기본이다. 참조 중인 기준정보를 삭제하지 않는다.
- 열차종류코드는 문자열 PK이며 열차나 운임이 참조하면 변경·삭제하지 않는다. 표시명만 수정한다.

DB 제약과 잠금 동작의 근거는 [MySQL FK 문서](https://dev.mysql.com/doc/refman/8.4/en/create-table-foreign-keys.html)와
[InnoDB 잠금 문서](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)를 참고한다.

