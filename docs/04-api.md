# API 명세

Base URL: /api/v1. health를 제외한 모든 업무 API는 예정 계약이다.
정확한 속성·필수값·enum·응답 스키마는 [openapi.json](openapi.json)의 components/schemas를 기준으로 한다.
아래 경로에는 /api/v1을 붙인다. JSON은 snake_case, ID는 양의 정수, 시간은 시간대 포함 ISO 8601이다.
PUBLIC은 비인증, MEMBER는 로그인한 회원 및 관리자, ADMIN은 관리자만 허용한다.
MEMBER 경로는 관리자라도 본인 리소스만 접근한다. 타인 운영 조회는 /admin을 이용한다.
본인 대상이 아니면 존재 여부를 숨기기 위해 404를 반환한다.
리스트는 items/page/size/total 형식이고 page는 1부터, size는 기본 20·최대 100이다.
예약·환불 목록은 created_at DESC, id DESC, 기준정보는 id ASC 정렬한다.
검색은 departure_at ASC, run_id ASC, 승하차 정차 ID ASC로 정렬한다.
PATCH는 최소 한 속성이 필요하고 알 수 없는 필드와 빈 객체를 거절한다.
이메일은 trim + 소문자 정규화 후 중복을 확인하고 비밀번호는 정규화하지 않는다.

## 엔드포인트

| Method | 경로 | 권한 | 기능 | 요청 본문 스키마 | 성공 코드 |
| --- | --- | --- | --- | --- | --- |
| GET | /health | PUBLIC | 프로세스 상태 확인 | — | 200 |
| POST | /auth/register | PUBLIC | 회원가입 | Register | 201 |
| POST | /auth/login | PUBLIC | 로그인 | Login | 200 |
| POST | /auth/logout | MEMBER | 전체 기기 토큰 무효화 | — | 200 |
| GET | /users/me | MEMBER | 본인 정보 | — | 200 |
| PATCH | /users/me | MEMBER | 본인 이름·연락처 수정 | UserPatch | 200 |
| POST | /users/me/password | MEMBER | 비밀번호 변경 및 전 토큰 무효화 | PasswordChange | 200 |
| GET | /stations | PUBLIC | 운영중인 역 목록 | — | 200 |
| GET | /runs | MEMBER | 직통 운행 검색 | — | 200 |
| GET | /runs/{run_id}/seats | MEMBER | 선택 구간 좌석 조회 | — | 200 |
| POST | /reservations | MEMBER | 여러 좌석 예약 | ReservationCreate | 201 |
| GET | /reservations | MEMBER | 본인 예약 목록 | — | 200 |
| GET | /reservations/{reservation_id} | MEMBER | 예약·승차권·결제·환불 상세 | — | 200 |
| POST | /reservations/{reservation_id}/cancel | MEMBER | 미결제 예약 전체 취소 | — | 200 |
| POST | /reservations/{reservation_id}/payments | MEMBER | 시연 결제 및 발권 | PaymentCreate | 201 |
| GET | /tickets/{ticket_id} | MEMBER | 본인 승차권 조회 | — | 200 |
| POST | /reservations/{reservation_id}/ticket-cancellations | MEMBER | 발권 승차권 선택 취소·환불 접수 | TicketCancel | 200 |
| GET | /refunds | MEMBER | 본인 환불 목록 | — | 200 |
| GET | /refunds/{refund_id} | MEMBER | 본인 환불 처리 상태 | — | 200 |
| GET | /admin/stations | ADMIN | 관리 stations 목록 | — | 200 |
| POST | /admin/stations | ADMIN | 관리 stations 등록 | StationCreate | 201 |
| PATCH | /admin/stations/{id} | ADMIN | 관리 stations 수정 | StationPatch | 200 |
| DELETE | /admin/stations/{id} | ADMIN | 미참조 stations 삭제 | — | 200 |
| GET | /admin/trains | ADMIN | 관리 trains 목록 | — | 200 |
| POST | /admin/trains | ADMIN | 관리 trains 등록 | TrainCreate | 201 |
| PATCH | /admin/trains/{id} | ADMIN | 관리 trains 수정 | TrainPatch | 200 |
| DELETE | /admin/trains/{id} | ADMIN | 미참조 trains 삭제 | — | 200 |
| GET | /admin/seats | ADMIN | 관리 seats 목록 | — | 200 |
| POST | /admin/seats | ADMIN | 관리 seats 등록 | SeatCreate | 201 |
| PATCH | /admin/seats/{id} | ADMIN | 관리 seats 수정 | SeatPatch | 200 |
| DELETE | /admin/seats/{id} | ADMIN | 미참조 seats 삭제 | — | 200 |
| GET | /admin/routes | ADMIN | 관리 routes 목록 | — | 200 |
| POST | /admin/routes | ADMIN | 관리 routes 등록 | RouteCreate | 201 |
| PATCH | /admin/routes/{id} | ADMIN | 관리 routes 수정 | RoutePatch | 200 |
| DELETE | /admin/routes/{id} | ADMIN | 미참조 routes 삭제 | — | 200 |
| GET | /admin/route-stops | ADMIN | 관리 route-stops 목록 | — | 200 |
| POST | /admin/route-stops | ADMIN | 관리 route-stops 등록 | RouteStopCreate | 201 |
| PATCH | /admin/route-stops/{id} | ADMIN | 관리 route-stops 수정 | RouteStopPatch | 200 |
| DELETE | /admin/route-stops/{id} | ADMIN | 미참조 route-stops 삭제 | — | 200 |
| GET | /admin/runs | ADMIN | 관리 runs 목록 | — | 200 |
| POST | /admin/runs | ADMIN | 관리 runs 등록 | RunCreate | 201 |
| PATCH | /admin/runs/{id} | ADMIN | 관리 runs 수정 | RunPatch | 200 |
| GET | /admin/run-stops | ADMIN | 관리 run-stops 목록 | — | 200 |
| POST | /admin/run-stops | ADMIN | 관리 run-stops 등록 | RunStopCreate | 201 |
| PATCH | /admin/run-stops/{id} | ADMIN | 관리 run-stops 수정 | RunStopPatch | 200 |
| DELETE | /admin/run-stops/{id} | ADMIN | 미참조 run-stops 삭제 | — | 200 |
| GET | /admin/fares | ADMIN | 관리 fares 목록 | — | 200 |
| POST | /admin/fares | ADMIN | 관리 fares 등록 | FareCreate | 201 |
| PATCH | /admin/fares/{id} | ADMIN | 관리 fares 수정 | FarePatch | 200 |
| DELETE | /admin/fares/{id} | ADMIN | 미참조 fares 삭제 | — | 200 |
| POST | /admin/runs/{run_id}/cancel | ADMIN | 운행 취소 및 환불 접수 | — | 200 |
| GET | /admin/users | ADMIN | 회원 목록 | — | 200 |
| PATCH | /admin/users/{user_id} | ADMIN | 회원 활성 여부 변경 | AdminUserPatch | 200 |
| GET | /admin/reservations | ADMIN | 예약·발권·결제·환불 운영 조회 | — | 200 |
| GET | /admin/refunds | ADMIN | 환불 현황 | — | 200 |
| POST | /admin/refunds/{refund_id}/process | ADMIN | 대기 환불 처리 또는 실패 환불 재시도 | RefundProcess | 200 |
| POST | /admin/tickets/{ticket_id}/boarding | ADMIN | 탑승 확인 | — | 201 |

결제 실패 시에도 정상 시연 처리 결과이므로 201 Payment(status=FAILED)를 반환한다.
멱등 재전송은 200이며 새로운 결제·발권을 만들지 않는다.
DELETE는 미참조 데이터에만 허용한다. 참조가 있으면 409 RESOURCE_IN_USE다.
운행은 DELETE하지 않고 전용 cancel을 사용한다. 운행 생성·일반 PATCH로 CANCELLED를 받을 수 없다.
예약이 존재하면 운행의 열차·노선·시간표·정차순서를 수정할 수 없다.
기존 운행이 참조하는 노선정차역·좌석 구성도 임의 변경하지 않는다.
관리자 회원 수정은 is_active만 받으며 권한 승격·비밀번호 조회 기능은 없다.
회원 비활성화 시 token_version을 증가시키되 기존 예약·결제 기록은 보존한다.

## 핵심 요청 예시

예약 생성 — POST /reservations:

~~~json
{"run_id":501,"boarding_run_stop_id":5011,"alighting_run_stop_id":5013,"passenger_count":2,"seat_ids":[101,102]}
~~~

반환 Reservation은 id, run_id, status, created_at, expires_at, total_amount와
tickets, payments, refunds를 포함한다. 최초 상태는 PENDING_PAYMENT, tickets는 HELD다.
사용자는 금액·사용자 ID·발권상태를 지정하지 않는다.

시연 결제 — POST /reservations/1001/payments, Idempotency-Key: demo-payment-1001-1:

~~~json
{"method":"DEMO_CARD","demo_result":"SUCCESS"}
~~~

승차권 선택 취소 — POST /reservations/1001/ticket-cancellations:

~~~json
{"ticket_ids":[2002]}
~~~

환불은 먼저 PENDING을 반환한다. 관리자가 process에 demo_result를 제출하여 성공·실패를 시연한다.
이미 SUCCEEDED인 환불의 성공 재전송은 기존 결과를 반환하고 다른 결과로 바꾸려 하면 409다.

## 공통 오류

~~~json
{"error":{"code":"SEAT_CONFLICT","message":"선택 구간에 이미 확보된 좌석입니다.","details":[]}}
~~~

| HTTP | code | 조건 |
| --- | --- | --- |
| 401 | AUTH_REQUIRED / TOKEN_EXPIRED | 인증 없음·만료·로그아웃 토큰 |
| 403 | ADMIN_REQUIRED | 관리자 권한 없음 |
| 404 | RESOURCE_NOT_FOUND | 없음 또는 소유권 없음 |
| 409 | EMAIL_DUPLICATE | 중복 이메일 |
| 409 | SEAT_CONFLICT | 겹치는 구간의 점유 좌석 |
| 409 | RESERVATION_EXPIRED / INVALID_STATE | 만료 또는 허용되지 않는 상태 전이 |
| 409 | IDEMPOTENCY_CONFLICT / ALREADY_PAID | 멱등키 본문 충돌 또는 중복 결제 |
| 409 | ALREADY_BOARDED / REFUND_LIMIT_EXCEEDED | 탑승 중복 또는 환불 한도 초과 |
| 409 | RESOURCE_IN_USE / RUN_TIME_CONFLICT | 참조 중인 데이터 또는 열차 운행 시간 충돌 |
| 422 | VALIDATION_ERROR | 필수값·인원·구간·운임 부재 등 입력 검증 |
| 503 | RETRY_LATER | 잠금 재시도 소진 |

오류 내부 DB 문자열·스택·토큰은 응답으로 노출하지 않는다.
현재 health 이외의 공통 오류 핸들러·업무 API·인증은 아직 구현되지 않았다.
