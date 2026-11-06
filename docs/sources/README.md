# 기준 문서와 텍스트 사본

사용자가 제공한 두 문서의 본문을 2026-11-06(한국시간)에 읽고 프로젝트에 반영했다.
사본은 본문을 비교·검색하기 위한 텍스트 추출본이다. 원본의 표·페이지·서식은 유지하지 않는다.

| 원문 | 로컬 사본 | 역할 |
| --- | --- | --- |
| [기차예약시스템 팀프로젝트 제안서](https://docs.google.com/document/d/1eDCdw0_zxvUQLHEWRPFBUaleSqtQ9oj-/edit) | [01-제안서.txt](01-제안서.txt) | 목적, 주요 기능, 14개 데이터, 팀원 역할, 개발 환경 |
| [기차예약시스템 업무분석서](https://docs.google.com/document/d/1lst6UsPt1-7TQZISew9ixknkWA5f3ZE3m_V1OhgDxf0/edit?tab=t.0) | [02-업무분석서.txt](02-업무분석서.txt) | 상세 업무, 요구사항, 구간 예약·결제·환불 규칙과 양식 예시 |

확인한 제안서는 이미 FastAPI를 사용 기술로 명시하고 있다.
프로젝트의 [설계서](../설계서.md)와 코드 환경에도 FastAPI를 적용했다.
원본 Drive 파일은 변경하지 않았다. 원문에 없는 세부 정책은 [설계 결정](../10-decisions.md)에 구분했다.

## 후속 첨부 DB 기준

사용자가 이어서 제공한 [ERD-reference.png](ERD-reference.png)는 DB 구조의 우선 기준이다.
열차종류와 좌석점유를 포함한 16개 엔터티, 열차종류코드 FK, 운행별 방향, 좌석점유 복합 PK를 반영했다.
위 두 문서의 텍스트 사본은 원문 기록으로 유지하며 14개 데이터 설명을 임의로 고치지 않는다.
최신 구현 설계와 이미지 밖의 운영 필드는 [DB 설계](../03-database.md)를 따른다.

파일 ID·MIME 유형·원본 수정 시각은 [source-metadata.json](source-metadata.json)에 기록했다.
