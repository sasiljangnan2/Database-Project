# SQLAlchemy 모델

db/001_schema.sql의 **16개 테이블**을 개별 Python 파일로 매핑했다.
app.models를 import하면 공통 Base.metadata에 모두 등록된다.
DB 담당자가 공통 모델을 관리하며 다른 담당자는 이 정의를 재사용한다.
필드·FK·PK 대응은 tests/test_shared_contract.py에서 검사한다.
실제 MySQL의 컬럼·NULL 허용·PK 일치는 선택 MySQL 테스트에서 확인한다.
앱 기동 시 create_all로 공유 DB를 변경하지 않는다.

BIGINT의 SQLite variant는 회원 HTTP 로직 단위 테스트용이다.
MySQL의 잠금·금액·구간 점유 무결성을 SQLite로 검증한 것으로 간주하지 않는다.

