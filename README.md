# Redmine → Google Sheets Sync

레드마인 이슈를 구글 스프레드시트에 자동으로 동기화하는 Python 프로그램입니다.
 
https://github.com/user-attachments/assets/15a3735a-aaec-4c54-85eb-6b9804c71d3a


---

## 개발 배경

레드마인에 이슈가 등록될 때마다 팀원 간 공유를 쉽게 하기 위해 스프레드시트에 정리해 사용했던 경험이 있습니다.
하지만 레드마인에서 파일을 수동으로 내려받아 스프레드시트에 붙여넣는 반복 작업이 번거로웠고, **누락되거나 정렬이 맞지 않는 문제**가 자주 발생했습니다.

이를 해결하고 **유형 및 버전별로 이슈를 편하게 관리**해 QA 업무 효율을 높이고자 이 자동화 프로그램을 만들었습니다.

---

## 사용 기술

| 기술 | 용도 |
| --- | --- |
| Python | 메인 프로그래밍 언어 |
| Google Sheets API (gspread) | 스프레드시트 자동 연동 |
| Google 서비스 계정 인증 (google-auth) | 구글 서비스 접근 |
| python-redmine (redminelib) | 레드마인 API 연동 |
| schedule | 주기적 자동 실행 |
| python-dotenv | 환경 변수(API 키 등) 분리 관리 |
| Claude Code | AI 코드 어시스턴트 활용 |

---

## 동작 흐름

```
레드마인 이슈 등록
      ↓
Python 프로그램이 레드마인 API로 이슈 수집
      ↓
버전별 / 우선순위별 자동 분류
      ↓
구글 스프레드시트 해당 시트에 자동 기록
      ↓
5분마다 자동 반복 실행
```

---

## 주요 기능

1. **버전별 시트 자동 생성** — 레드마인 목표버전에 따라 시트가 자동으로 생성됩니다. (예: `1.0.1_패치리스트`, `1.0.2_패치리스트` …)
2. **우선순위별 행 색상 자동 적용**
   - Critical → 빨강
   - Major → 주황
   - Normal → 흰색
   - Minor → 하늘색
3. **하이퍼링크 자동 삽입** — 링크 버튼 클릭 시 해당 레드마인 이슈 페이지로 바로 이동합니다.
4. **QA 데이터 보존** — 동기화 시에도 `QA담당자` / `QA확인여부` 수동 입력값이 유지됩니다.
5. **5분마다 자동 동기화** — 새 이슈는 자동 추가, 기존 이슈는 상태가 자동 갱신됩니다.
6. **보안 관리** — API 키와 인증 파일을 `.env` / `credentials.json`으로 분리해 코드에 민감 정보가 없도록 했습니다.

### 시트 컬럼 구성 (A~K)

| 링크 | # | 상태 | 유형 | 우선순위 | 제목 | 담당자 | 저자 | 진척도 | QA담당자 | QA확인여부 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

> `QA담당자`, `QA확인여부`(J·K열)는 QA팀이 직접 입력하는 칸이며, 동기화 시 덮어쓰지 않습니다.

---

## 설치 및 실행 방법

### 1. 저장소 클론 및 패키지 설치

```bash
git clone https://github.com/platypus9511/redmine-sheets-sync.git
cd redmine-sheets-sync
pip install -r requirements.txt
```

### 2. 구글 서비스 계정 준비

1. Google Cloud Console에서 프로젝트를 만들고 **Google Sheets API**를 활성화합니다.
2. 서비스 계정을 생성하고 JSON 키를 내려받아 `credentials.json` 이름으로 프로젝트 폴더에 넣습니다.
3. 동기화할 스프레드시트를 서비스 계정 이메일에 **편집자** 권한으로 공유합니다.

### 3. `.env` 파일 작성

프로젝트 폴더에 `.env` 파일을 만들고 아래 값을 입력합니다.

```env
REDMINE_URL=https://your-redmine-server.com
REDMINE_API_KEY=your_redmine_api_key
SPREADSHEET_ID=your_google_spreadsheet_id
```

> `SPREADSHEET_ID`는 스프레드시트 주소 `https://docs.google.com/spreadsheets/d/<여기>/edit` 부분입니다.

### 4. 실행

```bash
python main.py
```

실행 즉시 1회 동기화한 뒤 5분 간격으로 반복합니다. 종료는 `Ctrl+C`입니다.
`.env`나 `credentials.json`이 없거나 값이 비어 있으면 어떤 항목이 빠졌는지 안내 후 종료됩니다.

### 샘플 데이터로 테스트하기

레드마인 서버 없이 테스트하려면 `main.py`의 `get_issues()` 함수 본문을 아래로 바꾸면 `sample_data.py`의 테스트 이슈로 동작합니다.

```python
from sample_data import SAMPLE_ISSUES
return SAMPLE_ISSUES
```

---

## 프로젝트 구조

```
redmine-sheets-sync/
├── main.py            # 메인 동기화 프로그램
├── sample_data.py     # 테스트용 샘플 이슈 데이터
├── requirements.txt   # 필요 패키지 목록
├── .gitignore         # .env, credentials.json 등 업로드 제외
├── .env               # (직접 생성) API 키 등 환경 변수
└── credentials.json   # (직접 생성) 구글 서비스 계정 키
```

---

## 핵심 코드

### 1. 레드마인 API 연동

```python
def get_issues():
    rm = Redmine(REDMINE_URL, key=REDMINE_API_KEY)
    issues = rm.issue.filter(status_id='*')  # 모든 상태 이슈 수집
    return [_resource_to_dict(issue) for issue in issues]
```

API 키로 인증 후 전체 이슈를 가져와 구글 시트에 넣기 좋은 형태로 변환합니다. 실제 서버 연동 시 URL과 API 키만 바꾸면 바로 사용할 수 있도록 설계했습니다.

### 2. 보안 — API 키 분리 관리

```python
load_dotenv()
REDMINE_API_KEY = os.getenv('REDMINE_API_KEY', '')
SPREADSHEET_ID  = os.getenv('SPREADSHEET_ID', '')
```

API 키와 스프레드시트 ID를 하드코딩하지 않고 `.env`로 분리했으며, `.gitignore`에 등록해 GitHub에 올라가지 않도록 했습니다.

### 3. QA 데이터 보존

```python
qa_by_id = {
    row[1]: [row[9], row[10]]
    for row in existing_data[1:]
}
```

동기화 시 시트를 초기화하고 재작성하는데, QA팀이 수동 입력한 담당자·확인여부는 이슈 ID 기준으로 미리 저장했다가 재작성 시 복원합니다.

### 4. 5분마다 자동 실행

```python
sync_all()                                                  # 실행 즉시 1회 동기화
schedule.every(SYNC_INTERVAL_MINUTES).minutes.do(sync_all)  # 5분마다 자동 반복

while True:
    schedule.run_pending()
    time.sleep(2)
```

`schedule` 라이브러리로 주기 실행을 구현했고, 루프에 대기 시간을 두어 CPU 과부하를 방지했습니다.

### 5. 버전별 시트 자동 생성

```python
def get_or_create_sheet(spreadsheet, sheet_name):
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=sheet_name, rows=500, cols=len(HEADERS))
```

시트가 있으면 재사용하고, 없으면 새로 만듭니다.

### 6. 우선순위별 정렬

```python
issues = sorted(
    issues,
    key=lambda i: PRIORITY_ORDER.get(i.get('priority', {}).get('name', ''), 99)
)
```

Critical → Major → Normal → Minor 순으로 정렬하고, 우선순위가 없는 이슈는 맨 아래로 보냅니다.

### 7. 버전별 이슈 분류

```python
version_bucket = {}
for issue in issues:
    version = issue.get('fixed_version', {}).get('name', '미지정')
    version_bucket.setdefault(version, []).append(issue)
```

목표버전 기준으로 분류하며, 목표버전이 없는 이슈는 `미지정` 시트로 들어갑니다.

### 8. 오류 처리

```python
try:
    rm = Redmine(REDMINE_URL, key=REDMINE_API_KEY)
    issues = rm.issue.filter(status_id='*')
    return result
except AuthError:
    print("인증 실패 — REDMINE_API_KEY를 확인하세요.")
except ResourceNotFoundError:
    print("리소스를 찾을 수 없습니다 — REDMINE_URL을 확인하세요.")
except Exception as e:
    print(f"레드마인 연결 실패: {e}")

return []
```

인증 실패, URL 오류, 기타 오류를 구분해 안내하며, 오류가 나도 스케줄러는 멈추지 않고 다음 주기에 자동으로 재시도합니다.

---

## 트러블슈팅

### 1. 하이퍼링크가 수식 텍스트로 표시되는 문제

- **증상**: 셀에 링크 아이콘 대신 `=HYPERLINK("http://...", "🔗")` 텍스트가 그대로 출력됨
- **원인**: 구글 시트 API에서 `=HYPERLINK()` 수식이 제대로 렌더링되지 않는 경우 발생
- **해결**: 수식 대신 `updateCells` 요청으로 링크를 직접 삽입

```python
# 변경 전
f'=HYPERLINK("{url}","🔗")'

# 변경 후
'updateCells': {
    'rows': [{'values': [{
        'userEnteredValue': {'stringValue': '🔗'},
        'textFormatRuns': [{'format': {'link': {'uri': url}}}],
    }]}]
}
```

### 2. 헤더 중복 생성 문제

- **증상**: 동기화를 반복할 때마다 헤더 행이 2행, 3행에 계속 추가됨
- **원인**: `insert_row()` 사용 시 기존 행이 아래로 밀리면서 헤더가 중복 삽입됨
- **해결**: 헤더 존재 여부를 먼저 확인 → 있으면 `update()`로 덮어쓰기, 없으면 `insert_row()`로 삽입

```python
def ensure_header(worksheet):
    first_row = worksheet.row_values(1)
    if first_row == HEADERS:
        return                                  # 헤더 있으면 종료
    if first_row:
        worksheet.update([HEADERS], 'A1')       # 덮어쓰기
    else:
        worksheet.insert_row(HEADERS, index=1)  # 새로 삽입
```

### 3. 재실행 시 정렬 순서가 유지되지 않는 문제

- **증상**: 우선순위 순으로 정렬했는데 재실행 후 순서가 뒤섞임
- **원인**: 기존 이슈를 행 번호 기준으로 업데이트해 정렬 순서가 반영되지 않음
- **해결**: 헤더 아래 데이터를 전체 초기화한 뒤 정렬된 순서로 재작성

```python
# 전체 초기화
worksheet.batch_clear([f'A2:K{clear_end}'])

# 정렬된 순서로 재작성
worksheet.batch_update([{
    'range': f'B2:K{1 + len(data_rows)}',
    'values': data_rows,
}])
```

### 4. 동기화 시 QA 데이터가 삭제되는 문제

- **증상**: 동기화 후 QA팀이 입력한 `QA담당자`, `QA확인여부` 값이 사라짐
- **원인**: 전체 초기화 방식으로 재작성하면서 수동 입력 데이터도 함께 삭제됨
- **해결**: 초기화 전에 이슈 ID를 키로 QA 데이터를 저장해두었다가 재작성 시 복원

```python
# 초기화 전 QA 데이터 저장
qa_by_id = {
    row[1]: [row[9], row[10]]
    for row in existing_data[1:]
}

# 재작성 시 QA 데이터 복원
data_rows = [
    issue_to_row(issue) + qa_by_id.get(str(issue['id']), ['', ''])
    for issue in issues
]
```

---

## Author

**김도영 (Kim Do-young)** — Game QA
