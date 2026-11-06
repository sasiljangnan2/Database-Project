-- 이전 14개 테이블 스키마 전용 1회 수동 마이그레이션 초안.
-- 신규 16개 테이블 DB에는 실행하지 않는다. README.md의 사전 점검과 백업이 먼저다.
-- DDL은 자동 commit되며 전체 rollback되지 않는다. 실제 MySQL 실행 검증 전이다.
SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE train_types (
    code VARCHAR(30) PRIMARY KEY,
    name VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 기존 문자열 코드를 보존한다. 표시용 종류명은 적용 후 관리자가 수정한다.
INSERT INTO train_types (code, name)
SELECT type_code, type_code FROM (
    SELECT train_type AS type_code FROM trains
    UNION
    SELECT train_type AS type_code FROM fares
) AS old_types;

ALTER TABLE trains
    CHANGE COLUMN train_type train_type_code VARCHAR(30) NOT NULL,
    ADD CONSTRAINT fk_trains_type FOREIGN KEY (train_type_code) REFERENCES train_types(code);
ALTER TABLE fares
    CHANGE COLUMN train_type train_type_code VARCHAR(30) NOT NULL,
    ADD CONSTRAINT fk_fares_type FOREIGN KEY (train_type_code) REFERENCES train_types(code);

ALTER TABLE runs ADD COLUMN direction VARCHAR(50) NULL;
UPDATE runs AS r JOIN routes AS rt ON rt.id = r.route_id SET r.direction = rt.direction;
ALTER TABLE runs MODIFY COLUMN direction VARCHAR(50) NOT NULL;
-- 노선에만 있던 방향은 운행으로 옮긴다. 노선 단독 값은 반드시 백업에서 보존한다.
ALTER TABLE routes DROP COLUMN direction;
ALTER TABLE stations MODIFY COLUMN region VARCHAR(100) NULL COMMENT 'ERD 외 선택 메타데이터';

CREATE TABLE seat_occupancies (
    run_id BIGINT UNSIGNED NOT NULL,
    seat_id BIGINT UNSIGNED NOT NULL,
    segment_start_order SMALLINT UNSIGNED NOT NULL,
    ticket_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (run_id, seat_id, segment_start_order),
    INDEX idx_occupancy_ticket (ticket_id),
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (seat_id) REFERENCES seats(id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    CONSTRAINT fk_occupancy_segment FOREIGN KEY (run_id, segment_start_order)
        REFERENCES run_stops(run_id, stop_order),
    CHECK (segment_start_order > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 여러 구간 중 하나라도 충돌하면 INSERT 전체가 실패한다. IGNORE로 넘기지 않는다.
-- 승하차·좌석·상태의 무결성은 README의 사전 점검에서 확인한 DB에만 적용한다.
INSERT INTO seat_occupancies (run_id, seat_id, segment_start_order, ticket_id)
SELECT r.run_id, t.seat_id, s.stop_order, t.id
FROM tickets AS t
JOIN reservations AS r ON r.id = t.reservation_id
JOIN run_stops AS b ON b.id = t.boarding_run_stop_id AND b.run_id = r.run_id
JOIN run_stops AS a ON a.id = t.alighting_run_stop_id AND a.run_id = r.run_id
JOIN run_stops AS s ON s.run_id = r.run_id
    AND s.stop_order >= b.stop_order AND s.stop_order < a.stop_order
WHERE t.status IN ('HELD', 'ISSUED', 'BOARDED')
    AND (t.status <> 'HELD' OR (r.status = 'PENDING_PAYMENT'
        AND r.expires_at > UTC_TIMESTAMP(6) AND b.departure_at > UTC_TIMESTAMP(6)));
