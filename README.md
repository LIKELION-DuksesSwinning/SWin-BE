# SWin-BE

수영과 피부 관리를 함께 기록하는 서비스 **SWin**의 백엔드 저장소입니다. Django REST Framework 기반 API 서버로, 수영 기록·AI 피부 분석·주간 리포트·수영장 찾기·피부과 클리닉 연계 예약 기능을 제공합니다.

## 주요 기능

| 앱 | 기능 |
|---|---|
| `accounts` | 로그인/로그아웃(JWT), 온보딩, 약관 동의, 알림 설정, 프로필 |
| `schedules` | 수영/클리닉 일정 캘린더 관리 |
| `records` | 수영 기록 등록(전/후/추가), 증상 기록 |
| `AIanalysis` | 수영 전후 사진을 GPT-4o로 비교 분석해 피부 변화 패턴 진단 |
| `report` | 주간 수영/피부 리포트, 맞춤 케어(성분·제품) 및 수영 루틴 추천 |
| `pools` | 시/도 → 시/군구 → 읍/면/동 단계별 서울시 수영장 찾기 |
| `clinic` | 제휴 클리닉 조회, 예약 생성/확정/취소, 예약 가능 시간대 조회 |
| `notifications` | 알림 목록 조회 및 읽음 처리 |

## 기술 스택

- **Framework**: Django 6.0, Django REST Framework
- **Auth**: djangorestframework-simplejwt (JWT)
- **AI**: OpenAI API (GPT-4o)
- **DB**: SQLite (로컬 개발용)
- **배포**: EC2 + systemd(uwsgi) + nginx, GitHub Actions 자동 배포

## 시작하기

### 1. 클론 및 가상환경 설정

```bash
git clone <repo-url>
cd SWin-BE
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 직접 생성합니다(`.gitignore`에 포함되어 있어 저장소에는 없습니다. OpenAI API 키는 팀 내 보안 채널로 별도 전달받으세요).

```
OPENAI_API_KEY=your-openai-api-key
```

### 3. 데이터베이스 마이그레이션

```bash
python manage.py migrate
```

### 4. (선택) 지역/수영장 데이터 시드

수영장 찾기(`pools`) 기능을 테스트하려면 아래 명령으로 서울시 행정구역·수영장 데이터를 채워야 합니다. 원본 파일은 `seed_data/`에 포함되어 있습니다.

```bash
python manage.py seed_regions --file "seed_data/법정동코드 전체자료.txt"
python manage.py seed_pools --file "seed_data/서울시 수영장업 인허가 정보.csv"
```

### 5. 서버 실행

```bash
python manage.py runserver
```

기본적으로 `http://localhost:8000`에서 서버가 뜹니다. `develop`을 새로 pull 받은 뒤에는 2~5단계(의존성 설치, 마이그레이션)를 다시 실행해주세요.

## 프로젝트 구조

```
SWin-BE/
├── config/          # 프로젝트 설정, URL 라우팅
├── accounts/        # 사용자, 온보딩, 약관, 알림 설정
├── schedules/        # 캘린더/일정
├── records/          # 수영 기록
├── AIanalysis/       # AI 피부 분석
├── report/            # 주간 리포트, 루틴 추천
├── pools/             # 수영장 찾기
├── clinic/            # 클리닉 연계 예약
├── notifications/     # 알림
└── seed_data/          # 지역/수영장 시드용 원본 데이터
```

모든 API는 `/api/v1/{앱}/...` 형태로 제공되며, 인증이 필요한 엔드포인트는 `Authorization: Bearer <access_token>` 헤더가 필요합니다.

## 배포

`develop` 브랜치에 push되면 GitHub Actions(`Deploy (systemd-lite)`)가 실행되어 배포 서버에 반영됩니다.
