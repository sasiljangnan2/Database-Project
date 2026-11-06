# Pydantic 요청·응답 모델

docs/openapi.json의 components/schemas를 기준으로 공통 Pydantic 모델을 구현했다.
auth.py는 회원·인증, catalog.py는 기준정보·운행·검색, booking.py는 예약·결제·환불·탑승이다.
common.py의 APIModel·PatchModel·Page와 공통 오류를 재사용한다.
DB 모델을 API 응답으로 직접 노출하지 않는다. 비밀번호 해시를 반환하지 않는다.

PATCH의 생략 필드는 내부 기본값이 None이지만 실제 null 허용 여부는 필드 타입으로 검증한다.
저장할 때 반드시 model_dump(exclude_unset=True)를 사용한다. 빈 PATCH는 거절한다.
예약의 인원·중복 좌석 등 입력 검증은 공통 모델에 있고 DB 상태 검증은 서비스가 맡는다.

