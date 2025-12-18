# DB Plan 미태깅 원인 분석 리포트

> 생성일: 2025-12-18 09:44

---

## 요약

- 전체 미태깅 문서: **3개**
- ✅ COMMON_DOC_EXPECTED: 3개

### 원인 코드 설명

| 코드 | 의미 | 조치 |
|------|------|------|
| COMMON_DOC_EXPECTED | 공통 문서로 plan NULL이 정상 | 조치 불필요 (PASS) |
| MANIFEST_MISSING | manifest에 plan 정보 추가 필요 | manifest.yaml 수정 |
| NO_PLAN_DEFINED_IN_DB | product_plan 테이블에 plan 없음 | DB seed 추가 |
| DETECTOR_POSSIBLE | detector 개선으로 자동 감지 가능 | plan_detector 개선 |

---

## 상세 내역

| document_id | doc_type | source_path | product_id | plan_id | manifest_hit | reason | detail |
|-------------|----------|-------------|------------|---------|--------------|--------|--------|
| 8 | 사업방법서 | DB_사업방법서.pdf | 2 | NULL | ✅ | COMMON_DOC_EXPECTED | doc_type=사업방법서는 플랜 구분 없는 공통 문서 |
| 9 | 상품요약서 | DB_상품요약서.pdf | 2 | NULL | ✅ | COMMON_DOC_EXPECTED | doc_type=상품요약서는 플랜 구분 없는 공통 문서 |
| 10 | 약관 | DB_약관.pdf | 2 | NULL | ✅ | COMMON_DOC_EXPECTED | doc_type=약관는 플랜 구분 없는 공통 문서 |

---

## 후보 Plans (product_plan 테이블)

| plan_id:plan_name |
|-------------------|
| 11:남성-40세이하 |
| 12:남성-41세이상 |
| 13:여성-40세이하 |
| 14:여성-41세이상 |
| 15:공용-전연령 |

---

## 결론

**모든 미태깅 문서가 `COMMON_DOC_EXPECTED`로 분류되어 정상입니다.**

이 문서들은 플랜 구분 없이 모든 플랜에 공통으로 적용되는 문서이므로, `plan_id = NULL`이 의도된 동작입니다.
