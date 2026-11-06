# 데이터 접근

SQLAlchemy 조회·저장·잠금 쿼리를 배치한다. 서비스에서 전달한 Session을 사용한다.
repository 안에서 commit하거나 새 Session을 만들지 않는다.

users.py는 이메일·ID 조회와 FOR UPDATE 조회를 제공한다.
예약 담당자는 공통 ORM 모델을 사용해 별도 저장소 파일에서 조회를 구현한다.
잠금 순서와 점유 전체 INSERT·해제 규칙은 docs/03-database.md를 따른다.

