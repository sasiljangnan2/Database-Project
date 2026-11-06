# 기존 14개 테이블 DB의 ERD 변경 반영

신규 DB는 상위 폴더의 `001_schema.sql`과 `002_seed.sql`만 실행한다.
`003_reference_erd.sql`은 이 프로젝트에서 앞서 제공했던 **14개 테이블 스키마 전용** 수동 변경안이다.
신규 16개 테이블 DB나 구조를 별도로 수정한 DB에 그대로 적용하지 않는다.
Docker 초기화는 하위 `migrations` 폴더의 SQL을 자동 적용하지 않는다.
이 프로젝트 파일을 수정하는 과정에서는 실제 DB에 접속하거나 마이그레이션을 실행하지 않았다.

## 적용 순서

1. 쓰기 요청과 만료 정리 작업을 중지하고, DB 백업과 복구 방법을 확인한다.
2. 아래 사전 점검을 수행한다. 오류를 먼저 수정하고 백업 복제본에서 SQL을 실행한다.
3. `003_reference_erd.sql`을 순서대로 한 번 실행한다. 클라이언트의 오류 무시/계속 옵션은 사용하지 않는다.
4. 열차종류의 종류명은 기존 코드로 채워진다. 예를 들어 `EXPRESS`의 표시명을 `급행`으로 수정한다.
5. 16개 테이블, 열차종류 FK, 운행방향, 활성 승차권의 구간별 점유 수와 소유자를 대조한다.
6. 예약·결제·취소·만료의 서비스 코드가 좌석점유를 함께 관리하도록 구현한 뒤 쓰기를 재개한다.

DDL은 자동 commit되므로 전체 파일에 `ROLLBACK`을 실행해 되돌릴 수 없다.
중간 실패 시 재실행으로 넘기지 않고 적용 상태를 확인한다. 복구 기준은 적용 전 백업이다.
`routes.direction`은 `runs.direction`으로 복사한 뒤 제거한다.
아직 운행이 없는 노선의 과거 방향 값은 DB 백업에 보존한다.
원래 노선 구성·운행 순서는 이 SQL이 재배열하지 않는다.

## 사전 점검

- 기존 스키마에 `trains.train_type`, `fares.train_type`, `routes.direction`이 있고,
  `train_types`와 `seat_occupancies`는 없는지 확인한다.
- 모든 운행이 노선과 연결되고, 승차권 좌석이 운행에 배정된 열차의 좌석인지 확인한다.
- 승하차 일정이 예약의 운행에 속하고 `승차 stop_order < 하차 stop_order`인지 확인한다.
- 운행별 `run_stops.stop_order`가 1부터 연속되고, 시각이 실제 진행 순서와 일치하는지 확인한다.
- HELD는 결제대기 예약에 속해야 한다. 만료되거나 출발한 HELD는 만료 상태로 정리한다.
- 동일 운행·좌석·구간에 활성 승차권이 두 개 이상 있는지 다음 쿼리로 확인한다.

```sql
SELECT r.run_id, t.seat_id, s.stop_order, COUNT(*) AS claims
FROM tickets AS t
JOIN reservations AS r ON r.id = t.reservation_id
JOIN run_stops AS b ON b.id = t.boarding_run_stop_id AND b.run_id = r.run_id
JOIN run_stops AS a ON a.id = t.alighting_run_stop_id AND a.run_id = r.run_id
JOIN run_stops AS s ON s.run_id = r.run_id
    AND s.stop_order >= b.stop_order AND s.stop_order < a.stop_order
WHERE t.status IN ('HELD', 'ISSUED', 'BOARDED')
    AND (t.status <> 'HELD' OR (r.status = 'PENDING_PAYMENT'
        AND r.expires_at > UTC_TIMESTAMP(6) AND b.departure_at > UTC_TIMESTAMP(6)))
GROUP BY r.run_id, t.seat_id, s.stop_order
HAVING COUNT(*) > 1;
```

결과가 있으면 원인을 확인하고 중복 예약을 업무 절차로 해결한 다음 변경한다.
`INSERT IGNORE`, `REPLACE`, 충돌 행 삭제로 임의의 승차권을 남기지 않는다.
이 쿼리는 중복 점유만 확인하므로 잘못된 FK 조합이나 누락된 정차 일정까지 검증한 것으로 간주하지 않는다.
