# DB 설계

db/001_schema.sql은 MySQL 8.0.16 이상용 14개 테이블 초기 스키마다.
원문 속성에 처리에 필요한 운영 필드를 추가했다. 상세 목록은 실제 SQL을 기준으로 한다.
운영 DB 적용 검증과 ORM 모델 구현은 남아 있다.

관계도 원본은 [ERD.mmd](ERD.mmd)다. 복합 UNIQUE·인덱스·CHECK와 NULL 허용 여부는
`db/001_schema.sql`을 기준으로 확인한다.

| 원문 데이터 | 테이블 | 핵심 제약 및 연결 |
| --- | --- | --- |
| 회원 | users | email UNIQUE, token_version, role |
| 역 | stations | 역명·지역, is_active |
| 열차 | trains | identifier UNIQUE, train_type, is_active |
| 좌석 | seats | UNIQUE(train_id, carriage_no, seat_number) |
| 노선 | routes | name, direction, is_active |
| 노선 정차역 | route_stops | UNIQUE(route_id, stop_order), 역 반복 허용 |
| 운행 | runs | train_id, route_id, service_date, status |
| 운행 정차 일정 | run_stops | UNIQUE(run_id, stop_order), 노선 정차역 연결 |
| 구간 운임 | fares | 출발·도착·열차종류·등급 UNIQUE, amount >= 0 |
| 예약 | reservations | user_id, run_id, 기한·상태·총액 |
| 승차권 | tickets | 예약·좌석·승하차 정차·운임, 확정금액·상태 |
| 결제 | payments | 예약·시도·성공/실패·멱등키, 예약당 성공 1건 |
| 환불 | refunds | 결제·승차권·사유·상태, 승차권당 1건 |
| 탑승 확인 | boarding_checks | ticket_id UNIQUE, 처리 관리자·일시 |

## 관계

회원 1:N 예약, 열차 1:N 좌석·운행, 노선 1:N 노선정차역·운행,
운행 1:N 운행정차일정·예약, 예약 1:N 승차권·결제시도,
결제 1:N 환불, 승차권 1:0..1 환불·탑승확인이다.
승차권의 승차/하차는 각각 운행정차일정을 가리킨다.

## 저장 규칙

- 금액은 KRW 정수 BIGINT. 합계는 서버에서 계산하며 브라우저 금액을 신뢰하지 않는다.
- DATETIME(6)은 애플리케이션에서 UTC로 변환해 저장한다. API는 시간대 포함 ISO 8601을 사용한다.
- service_date는 편성 시작일, 검색 departure_date는 Asia/Seoul 기준 승차역 출발일이다.
- 원문과 달리 reservations.run_id, expires_at, total_amount를 추가했다.
- run_stops.stop_order는 운행 시점의 정차순서 스냅샷이다. 운행이 있으면 노선 정차 구성은 변경 금지다.
- 기준정보에 이력이 연결되면 물리 삭제를 거절하고 is_active=false를 사용한다.
- FK는 RESTRICT를 기본으로 하며 회계·승차 기록을 cascade 삭제하지 않는다.
- fares 변경 후에도 tickets.confirmed_amount와 reservations.total_amount는 유지한다.

## DB 제약만으로 보장되지 않는 항목

승하차 일정이 같은 운행인지, 좌석이 운행 열차 소속인지, 운임 조건 일치,
합계·인원수, 동일 열차 운행 시간 겹침, 구간 중복은 서비스 트랜잭션에서 검증한다.
CHECK와 UNIQUE만으로 구간 겹침을 방지했다고 간주하지 않는다.

예약은 해당 trains 행을 SELECT ... FOR UPDATE로 잠근 뒤 run·seat·기존 점유를 검증한다.
동일 열차 작업을 직렬화하는 MVP 방식으로 성능보다 정확성을 우선한다.
예약·취소·결제·만료·운행취소·운행편성도 동일한 잠금 규칙에 참여해야 한다.
잠금 순서: train → run → reservation → ticket(ID 오름차순) → payment → refund.
이전 조회 결과를 신뢰하지 않고 잠금 후 재조회한다. 여러 열차는 ID 오름차순으로 잠근다.
deadlock 발생 시 전체 rollback 후 최대 2회 재시도하고 실패하면 재시도 가능한 오류를 반환한다.

