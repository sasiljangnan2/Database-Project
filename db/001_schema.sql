-- 첨부 ERD 기준 16개 테이블. 신규 개발 DB 초기화용. MySQL 8.0.16+ / InnoDB.
SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    role VARCHAR(10) NOT NULL DEFAULT 'MEMBER',
    token_version INT UNSIGNED NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL,
    CHECK (role IN ('MEMBER', 'ADMIN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE stations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    region VARCHAR(100) NULL COMMENT 'ERD 외 선택 메타데이터',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE train_types (
    code VARCHAR(30) PRIMARY KEY,
    name VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE trains (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(50) NOT NULL UNIQUE,
    train_type_code VARCHAR(30) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_trains_type FOREIGN KEY (train_type_code) REFERENCES train_types(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE seats (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    train_id BIGINT UNSIGNED NOT NULL,
    carriage_no SMALLINT UNSIGNED NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    seat_class VARCHAR(20) NOT NULL,
    UNIQUE (train_id, carriage_no, seat_number),
    FOREIGN KEY (train_id) REFERENCES trains(id),
    CHECK (carriage_no > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE routes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE route_stops (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    route_id BIGINT UNSIGNED NOT NULL,
    station_id BIGINT UNSIGNED NOT NULL,
    stop_order SMALLINT UNSIGNED NOT NULL,
    UNIQUE (route_id, stop_order),
    FOREIGN KEY (route_id) REFERENCES routes(id),
    FOREIGN KEY (station_id) REFERENCES stations(id),
    CHECK (stop_order > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE runs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    train_id BIGINT UNSIGNED NOT NULL,
    route_id BIGINT UNSIGNED NOT NULL,
    service_number VARCHAR(30) NOT NULL,
    service_date DATE NOT NULL,
    status VARCHAR(15) NOT NULL DEFAULT 'ON_SALE',
    direction VARCHAR(50) NOT NULL,
    UNIQUE (service_number, service_date),
    INDEX idx_runs_train_date (train_id, service_date),
    FOREIGN KEY (train_id) REFERENCES trains(id),
    FOREIGN KEY (route_id) REFERENCES routes(id),
    CHECK (status IN ('ON_SALE', 'CLOSED', 'CANCELLED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE run_stops (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT UNSIGNED NOT NULL,
    route_stop_id BIGINT UNSIGNED NOT NULL,
    stop_order SMALLINT UNSIGNED NOT NULL,
    arrival_at DATETIME(6) NULL,
    departure_at DATETIME(6) NULL,
    UNIQUE (run_id, stop_order),
    UNIQUE (run_id, route_stop_id),
    INDEX idx_stops_departure (departure_at),
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (route_stop_id) REFERENCES route_stops(id),
    CHECK (stop_order > 0),
    CHECK (arrival_at IS NOT NULL OR departure_at IS NOT NULL),
    CHECK (arrival_at IS NULL OR departure_at IS NULL OR arrival_at <= departure_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE fares (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    departure_station_id BIGINT UNSIGNED NOT NULL,
    arrival_station_id BIGINT UNSIGNED NOT NULL,
    train_type_code VARCHAR(30) NOT NULL,
    seat_class VARCHAR(20) NOT NULL,
    amount BIGINT NOT NULL,
    UNIQUE (departure_station_id, arrival_station_id, train_type_code, seat_class),
    FOREIGN KEY (departure_station_id) REFERENCES stations(id),
    FOREIGN KEY (arrival_station_id) REFERENCES stations(id),
    CONSTRAINT fk_fares_type FOREIGN KEY (train_type_code) REFERENCES train_types(code),
    CHECK (departure_station_id <> arrival_station_id),
    CHECK (amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE reservations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    run_id BIGINT UNSIGNED NOT NULL,
    status VARCHAR(25) NOT NULL DEFAULT 'PENDING_PAYMENT',
    created_at DATETIME(6) NOT NULL,
    expires_at DATETIME(6) NOT NULL,
    total_amount BIGINT NOT NULL,
    INDEX idx_reservation_user (user_id, created_at),
    INDEX idx_reservation_expiry (status, expires_at),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (run_id) REFERENCES runs(id),
    CHECK (total_amount >= 0),
    CHECK (expires_at > created_at),
    CHECK (status IN ('PENDING_PAYMENT', 'PAID', 'PARTIALLY_CANCELLED', 'CANCELLED', 'EXPIRED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tickets (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    reservation_id BIGINT UNSIGNED NOT NULL,
    seat_id BIGINT UNSIGNED NOT NULL,
    boarding_run_stop_id BIGINT UNSIGNED NOT NULL,
    alighting_run_stop_id BIGINT UNSIGNED NOT NULL,
    fare_id BIGINT UNSIGNED NOT NULL,
    confirmed_amount BIGINT NOT NULL,
    status VARCHAR(15) NOT NULL DEFAULT 'HELD',
    issued_at DATETIME(6) NULL,
    cancelled_at DATETIME(6) NULL,
    UNIQUE (reservation_id, seat_id),
    INDEX idx_ticket_occupancy (seat_id, status, boarding_run_stop_id, alighting_run_stop_id),
    FOREIGN KEY (reservation_id) REFERENCES reservations(id),
    FOREIGN KEY (seat_id) REFERENCES seats(id),
    FOREIGN KEY (boarding_run_stop_id) REFERENCES run_stops(id),
    FOREIGN KEY (alighting_run_stop_id) REFERENCES run_stops(id),
    FOREIGN KEY (fare_id) REFERENCES fares(id),
    CHECK (boarding_run_stop_id <> alighting_run_stop_id),
    CHECK (confirmed_amount >= 0),
    CHECK (status IN ('HELD', 'ISSUED', 'BOARDED', 'CANCELLED', 'EXPIRED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 각 행은 실제 운행 순서의 [segment_start_order, segment_start_order + 1) 점유다.
-- 승차권의 [승차순서, 하차순서) 전체를 같은 트랜잭션에서 INSERT한다.
-- 중복 키 발생 시 예약 전체를 rollback한다. INSERT IGNORE / REPLACE는 사용하지 않는다.
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

CREATE TABLE payments (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    reservation_id BIGINT UNSIGNED NOT NULL,
    amount BIGINT NOT NULL,
    method VARCHAR(20) NOT NULL,
    status VARCHAR(15) NOT NULL,
    idempotency_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    request_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    created_at DATETIME(6) NOT NULL,
    -- MySQL UNIQUE permits multiple NULLs; only SUCCEEDED reserves the parent ID.
    successful_reservation_id BIGINT UNSIGNED GENERATED ALWAYS AS
        (CASE WHEN status = 'SUCCEEDED' THEN reservation_id ELSE NULL END) STORED,
    UNIQUE (reservation_id, idempotency_key),
    UNIQUE (successful_reservation_id),
    FOREIGN KEY (reservation_id) REFERENCES reservations(id),
    CHECK (amount >= 0),
    CHECK (method IN ('DEMO_CARD', 'DEMO_TRANSFER')),
    CHECK (status IN ('SUCCEEDED', 'FAILED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE refunds (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    payment_id BIGINT UNSIGNED NOT NULL,
    ticket_id BIGINT UNSIGNED NOT NULL UNIQUE,
    amount BIGINT NOT NULL,
    reason VARCHAR(30) NOT NULL,
    status VARCHAR(15) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME(6) NOT NULL,
    processed_at DATETIME(6) NULL,
    INDEX idx_refund_status (status),
    FOREIGN KEY (payment_id) REFERENCES payments(id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    CHECK (amount >= 0),
    CHECK (reason IN ('USER_CANCELLED', 'RUN_CANCELLED')),
    CHECK (status IN ('PENDING', 'SUCCEEDED', 'FAILED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE boarding_checks (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ticket_id BIGINT UNSIGNED NOT NULL UNIQUE,
    checked_by BIGINT UNSIGNED NOT NULL,
    checked_at DATETIME(6) NOT NULL,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (checked_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
