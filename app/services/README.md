# 업무 서비스

예약, 결제, 취소, 환불과 탑승 확인 트랜잭션을 담당한다.
동시성 처리 순서와 상태 규칙은 docs/05-business-rules.md를 따른다.
commit은 서비스 작업 단위당 한 번 수행한다.

auth.py의 회원가입·로그인·로그아웃·정보 수정·비밀번호 변경은 구현했다.
다른 업무 서비스는 각 담당자가 기능별 파일로 추가한다. 인증 라우터 파일에 예약 기능을 넣지 않는다.
보호 API는 app/api/dependencies.py의 CurrentUser 또는 AdminUser를 받는다.

