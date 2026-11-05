-- 가상 기준정보. 사용자/관리자 계정은 비밀번호 해시 생성 기능 구현 후 추가한다.
SET NAMES utf8mb4;
SET time_zone = '+00:00';
INSERT INTO stations (id, name, region) VALUES
    (1, 'A역', '가상지역 A'), (2, 'B역', '가상지역 B'), (3, 'C역', '가상지역 C');
INSERT INTO trains (id, identifier, train_type) VALUES (1, 'TRAIN-010', 'EXPRESS');
INSERT INTO seats (id, train_id, carriage_no, seat_number, seat_class) VALUES
    (101, 1, 1, '1A', 'STANDARD'), (102, 1, 1, '1B', 'STANDARD');
INSERT INTO routes (id, name, direction) VALUES (1, 'A~C 시연노선', 'A_TO_C');
INSERT INTO route_stops (id, route_id, station_id, stop_order) VALUES
    (1, 1, 1, 1), (2, 1, 2, 2), (3, 1, 3, 3);
-- 날짜는 시연일에 맞게 새로운 운행으로 추가한다. 아래 예시는 한국시간 09:00~10:20.
INSERT INTO runs (id, train_id, route_id, service_number, service_date, status)
VALUES (501, 1, 1, 'T101', '2026-12-01', 'ON_SALE');
INSERT INTO run_stops (id, run_id, route_stop_id, stop_order, arrival_at, departure_at) VALUES
    (5011, 501, 1, 1, NULL, '2026-12-01 00:00:00'),
    (5012, 501, 2, 2, '2026-12-01 00:40:00', '2026-12-01 00:45:00'),
    (5013, 501, 3, 3, '2026-12-01 01:20:00', NULL);
INSERT INTO fares (id, departure_station_id, arrival_station_id, train_type, seat_class, amount)
VALUES (901, 1, 3, 'EXPRESS', 'STANDARD', 30000),
       (902, 1, 2, 'EXPRESS', 'STANDARD', 15000),
       (903, 2, 3, 'EXPRESS', 'STANDARD', 15000);
