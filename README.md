# Beauty Trend Dashboard

매일 09:00 KST에 네이버 Open API로 데이터를 페치해 정적 HTML을 빌드하고
GitHub Pages로 자동 배포하는 파이프라인입니다.

> 이 폴더는 `ai-driven-development` 저장소의 하위 프로젝트입니다.
> 워크플로우 파일은 **저장소 루트**의 `.github/workflows/daily-refresh.yml` 에 있습니다.

## 구조

```
ai-driven-development/
├── .github/workflows/daily-refresh.yml        ← cron 트리거 + Pages 배포
└── BeautyTrendDashboard/                      ← 이 프로젝트
    ├── scripts/refresh.py                     ← 데이터 페치 + HTML 생성
    ├── templates/dashboard.html               ← /* __SNAPSHOT_PLACEHOLDER__ */ 자리
    ├── docs/                                  ← 빌드 결과 (Pages 서빙 대상)
    │   └── index.html                         ← 첫 실행 후 생성됨
    ├── requirements.txt
    └── README.md
```

## 첫 셋업 (총 5분)

### 1. 네이버 Open API 키 발급
<https://developers.naver.com/main/> → Application 등록 →
**검색**, **데이터랩(검색어 트렌드)**, **데이터랩(쇼핑인사이트)** 세 개 활성화 →
Client ID 와 Client Secret 복사.

### 2. GitHub Secrets 등록
저장소 페이지 → **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `NAVER_CLIENT_ID` | 1단계 Client ID |
| `NAVER_CLIENT_SECRET` | 1단계 Client Secret |

### 3. GitHub Pages 활성화
저장소 페이지 → **Settings → Pages**:
- **Source**: **GitHub Actions** 를 선택 (Deploy from a branch 아님)

### 4. 첫 빌드 트리거
**Actions → Beauty Dashboard - Daily Refresh → Run workflow** 클릭.
- 1-2분 뒤 `https://jaugkoo.github.io/ai-driven-development/` 에서 대시보드 확인.
- 이후 매일 09:00 KST에 자동 갱신.

## 로컬 테스트

```bash
cd BeautyTrendDashboard
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export NAVER_CLIENT_ID=...
export NAVER_CLIENT_SECRET=...
python scripts/refresh.py
# → docs/index.html 생성, 브라우저로 열어 확인
```

## 커스터마이즈

`scripts/refresh.py` 상단의 Config 섹션을 수정:
- `KEYWORD_GROUPS`: 검색 트렌드 키워드 (최대 5그룹, 그룹당 5개)
- `SHOPPING_CATEGORIES`: 데이터랩 쇼핑인사이트 카테고리 코드
- `SHOP_QUERY`, `NEWS_QUERY`: 쇼핑·뉴스 검색어
- `LOOKBACK_DAYS`: 시계열 추이 기간 (기본 14)

## 비용

- GitHub Actions: public repo 무제한
- GitHub Pages: 무료
- 네이버 Open API: 25,000건/일 무료 (이 워크플로우는 4건/일 사용)

## 트러블슈팅

- **401 Unauthorized**: Secrets 오타 또는 네이버 개발자센터에서 API 미활성화
- **429 Too Many Requests**: 호출량 초과 (드묾) — 다음 날 자동 복구
- **Pages 404**: Settings → Pages 에서 Source가 "GitHub Actions" 로 설정되어 있는지 확인
- **commit 실패**: workflow `permissions: contents: write` 가 필요 (이미 설정됨)
