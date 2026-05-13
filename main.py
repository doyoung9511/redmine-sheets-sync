#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
레드마인 이슈를 목표버전(마일스톤)별 구글 스프레드시트 시트에 자동 정리
주기적으로 실행하면 새 이슈 추가 및 기존 이슈 상태 갱신이 자동으로 이루어짐
"""

import os
import time
import schedule
import gspread
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# .env 파일에서 환경 변수 로드
load_dotenv()

# ==================== 설정 ====================

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

CREDENTIALS_FILE = 'credentials.json'
SPREADSHEET_ID   = os.getenv('SPREADSHEET_ID', '')

# 레드마인 서버 주소
REDMINE_URL     = 'http://localhost/redmine'
# 레드마인 API 키 → .env 파일의 REDMINE_API_KEY에서 읽어옴
REDMINE_API_KEY = os.getenv('REDMINE_API_KEY', '')

# 시트 이름 형식: "{버전}_패치리스트" (예: 1.42.1_패치리스트)
SHEET_SUFFIX = '_패치리스트'

# 컬럼 헤더 (A~K, 총 11열) — 맨 앞에 링크 열 추가
HEADERS = ['링크', '#', '상태', '유형', '우선순위', '제목', '담당자', '저자', '진척도', 'QA담당자', 'QA확인여부']

# 우선순위별 행 배경색 (RGB, 각 채널 0.0~1.0)
PRIORITY_ROW_COLORS = {
    'Critical': {'red': 1.0,  'green': 0.0,  'blue': 0.0 },   # 빨강
    'Major':    {'red': 1.0,  'green': 0.6,  'blue': 0.0 },   # 주황
    'Normal':   {'red': 1.0,  'green': 1.0,  'blue': 1.0 },   # 흰색
    'Minor':    {'red': 0.53, 'green': 0.81, 'blue': 0.98},   # 하늘색
}

# 우선순위 정렬 순서 (낮은 숫자가 위로)
PRIORITY_ORDER = {'Critical': 0, 'Major': 1, 'Normal': 2, 'Minor': 3}


# ==================== 샘플 데이터 ====================
# 실제 레드마인 연동 시에는 아래 SAMPLE_ISSUES를 사용하지 않음
# 테스트가 필요할 때는 get_issues() 함수 마지막 줄을 주석 참고

# SAMPLE_ISSUES = [
SAMPLE_ISSUES = [
    # ── 버전 1.42.1 ──────────────────────────────────────
    {
        'id': 2001,
        'subject':      '로그인 페이지 500 오류 발생',
        'status':       {'name': '해결'},
        'tracker':      {'name': '결함'},
        'priority':     {'name': 'Critical'},
        'assigned_to':  {'name': '김철수'},
        'author':       {'name': '이팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.1'},
    },
    {
        'id': 2002,
        'subject':      '결제 모듈 예외 미처리 버그',
        'status':       {'name': '해결'},
        'tracker':      {'name': '결함'},
        'priority':     {'name': 'Critical'},
        'assigned_to':  {'name': '박민준'},
        'author':       {'name': '이팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.1'},
    },
    {
        'id': 2003,
        'subject':      'API 응답 속도 개선',
        'status':       {'name': '해결'},
        'tracker':      {'name': '새기능'},
        'priority':     {'name': 'Major'},
        'assigned_to':  {'name': '최수진'},
        'author':       {'name': '박팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.1'},
    },
    {
        'id': 2004,
        'subject':      '검색 필터 조건 초기화 문제',
        'status':       {'name': '해결'},
        'tracker':      {'name': '결함'},
        'priority':     {'name': 'Major'},
        'assigned_to':  {'name': '강현우'},
        'author':       {'name': '김팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.1'},
    },
    {
        'id': 2005,
        'subject':      '마이페이지 UI 개선',
        'status':       {'name': '해결'},
        'tracker':      {'name': '새기능'},
        'priority':     {'name': 'Normal'},
        'assigned_to':  {'name': '윤지영'},
        'author':       {'name': '박팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.1'},
    },
    {
        'id': 2006,
        'subject':      '공지사항 목록 페이지네이션 구현',
        'status':       {'name': '해결'},
        'tracker':      {'name': '새기능'},
        'priority':     {'name': 'Normal'},
        'assigned_to':  {'name': '임성훈'},
        'author':       {'name': '이팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.1'},
    },
    {
        'id': 2007,
        'subject':      '도움말 페이지 오타 관련 문의',
        'status':       {'name': '해결'},
        'tracker':      {'name': '문의'},
        'priority':     {'name': 'Minor'},
        'assigned_to':  {'name': '한소희'},
        'author':       {'name': '김팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.1'},
    },
    # ── 버전 1.42.2 ──────────────────────────────────────
    {
        'id': 2008,
        'subject':      '데이터베이스 연결 타임아웃',
        'status':       {'name': '해결'},
        'tracker':      {'name': '결함'},
        'priority':     {'name': 'Critical'},
        'assigned_to':  {'name': '이영희'},
        'author':       {'name': '이팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.2'},
    },
    {
        'id': 2009,
        'subject':      '프로필 이미지 업로드 오류',
        'status':       {'name': '해결'},
        'tracker':      {'name': '결함'},
        'priority':     {'name': 'Major'},
        'assigned_to':  {'name': '정다혜'},
        'author':       {'name': '박팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.2'},
    },
    {
        'id': 2010,
        'subject':      '이메일 알림 템플릿 수정 문의',
        'status':       {'name': '해결'},
        'tracker':      {'name': '문의'},
        'priority':     {'name': 'Normal'},
        'assigned_to':  {'name': '조현아'},
        'author':       {'name': '김팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.2'},
    },
    {
        'id': 2011,
        'subject':      '다크모드 지원 추가',
        'status':       {'name': '해결'},
        'tracker':      {'name': '새기능'},
        'priority':     {'name': 'Minor'},
        'assigned_to':  {'name': '임성훈'},
        'author':       {'name': '이팀장'},
        'done_ratio':   50,
        'fixed_version':{'name': '1.42.2'},
    },
]
# ]   ← 샘플 데이터 사용 시 위 닫는 대괄호 주석 해제, 아래 SAMPLE_ISSUES = [ 주석 처리


# ==================== 레드마인 데이터 로드 ====================

def _safe_get(resource, attr):
    """redminelib 리소스에서 속성을 안전하게 가져옴 (미설정 필드는 None 반환)"""
    try:
        return getattr(resource, attr)
    except Exception:
        return None


def _resource_to_dict(issue):
    """
    redminelib Resource 객체 → 샘플 데이터와 동일한 딕셔너리 형식으로 변환.
    assigned_to / fixed_version 같은 선택 필드는 없을 수 있으므로 안전하게 처리.
    """
    assigned = _safe_get(issue, 'assigned_to')
    version  = _safe_get(issue, 'fixed_version')
    return {
        'id':            issue.id,
        'subject':       issue.subject,
        'status':        {'name': issue.status.name},
        'tracker':       {'name': issue.tracker.name},
        'priority':      {'name': issue.priority.name},
        'assigned_to':   {'name': assigned.name if assigned else '미배정'},
        'author':        {'name': issue.author.name},
        'done_ratio':    issue.done_ratio or 0,
        'fixed_version': {'name': version.name if version else '미지정'},
    }


def get_issues():
    """
    레드마인 API에서 모든 프로젝트의 이슈를 가져와 딕셔너리 목록으로 반환.

    샘플 데이터로 테스트하려면:
        return SAMPLE_ISSUES
    """
    from redminelib import Redmine
    from redminelib.exceptions import AuthError, ImpersonateError, ResourceNotFoundError

    print(f"레드마인 이슈를 가져오는 중... ({REDMINE_URL})")
    try:
        rm     = Redmine(REDMINE_URL, key=REDMINE_API_KEY)
        # status_id='*' → 열린/닫힌 이슈 전부 가져옴
        issues = rm.issue.filter(status_id='*')
        result = [_resource_to_dict(issue) for issue in issues]
        print(f"  {len(result)}개 이슈 로드 완료")
        return result

    except AuthError:
        print(f"  [오류] 인증 실패 — REDMINE_API_KEY를 확인하세요.")
    except ResourceNotFoundError:
        print(f"  [오류] 리소스를 찾을 수 없습니다 — REDMINE_URL을 확인하세요.")
    except Exception as e:
        print(f"  [오류] 레드마인 연결 실패: {e}")

    return []   # 오류 시 빈 목록 반환 → 스케줄러는 계속 실행


# ==================== Google Sheets 연결 ====================

def connect_spreadsheet():
    """서비스 계정 인증 후 스프레드시트 객체 반환"""
    print("Google Sheets API에 연결 중...")
    credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client      = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    print(f"  연결 성공: '{spreadsheet.title}'")
    return spreadsheet


# ==================== 시트 관리 ====================

def get_or_create_sheet(spreadsheet, sheet_name):
    """시트가 없으면 생성, 있으면 기존 시트 반환"""
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"  '{sheet_name}' 시트 없음 → 새로 생성")
        return spreadsheet.add_worksheet(title=sheet_name, rows=500, cols=len(HEADERS))


def ensure_header(worksheet):
    """헤더 행이 없거나 다르면 설정 (중복 삽입 방지)"""
    first_row = worksheet.row_values(1)
    if first_row == HEADERS:
        return
    if first_row:
        # 잘못된 헤더가 있으면 1행을 덮어쓰기 (insert 하면 행이 추가되므로 update 사용)
        worksheet.update([HEADERS], 'A1')
    else:
        # 완전히 빈 시트면 삽입
        worksheet.insert_row(HEADERS, index=1)


# ==================== 데이터 변환 ====================

def issue_to_row(issue):
    """이슈 딕셔너리 → B~I 컬럼 데이터 8개 반환 (A열 링크는 build_hyperlink_request로 별도 삽입)"""
    done_ratio = issue.get('done_ratio', 0)
    return [
        issue['id'],                                          # # (이슈 번호)   → B열
        issue.get('status',      {}).get('name', ''),         # 상태            → C열
        issue.get('tracker',     {}).get('name', ''),         # 유형            → D열
        issue.get('priority',    {}).get('name', ''),         # 우선순위        → E열
        issue.get('subject', ''),                             # 제목            → F열
        issue.get('assigned_to', {}).get('name', '미배정'),   # 담당자          → G열
        issue.get('author',      {}).get('name', ''),         # 저자            → H열
        f"{done_ratio}%",                                     # 진척도          → I열
    ]


# ==================== 행 배경색 · 하이퍼링크 API 요청 생성 ====================

def build_color_request(sheet_id, row_index_0, color):
    """단일 행 배경색 변경 API 요청 생성 (row_index_0: 0-indexed)"""
    return {
        'repeatCell': {
            'range': {
                'sheetId':       sheet_id,
                'startRowIndex': row_index_0,
                'endRowIndex':   row_index_0 + 1,
            },
            'cell': {
                'userEnteredFormat': {'backgroundColor': color}
            },
            'fields': 'userEnteredFormat.backgroundColor',
        }
    }


def build_hyperlink_request(sheet_id, row_index_0, url):
    """A열 단일 셀에 하이퍼링크 삽입 API 요청 생성 (row_index_0: 0-indexed)"""
    return {
        'updateCells': {
            'rows': [{
                'values': [{
                    'userEnteredValue': {'stringValue': '🔗'},
                    'textFormatRuns': [{
                        'startIndex': 0,
                        'format': {'link': {'uri': url}},
                    }],
                }]
            }],
            'fields': 'userEnteredValue,textFormatRuns',
            'range': {
                'sheetId':          sheet_id,
                'startRowIndex':    row_index_0,
                'endRowIndex':      row_index_0 + 1,
                'startColumnIndex': 0,
                'endColumnIndex':   1,
            },
        }
    }


# ==================== 버전별 시트 동기화 ====================

def sync_version_sheet(spreadsheet, version, issues):
    """
    특정 버전의 이슈를 해당 시트에 동기화.

    동작:
      1. 기존 QA 데이터(QA담당자·QA확인여부) 보존
      2. 헤더 아래 데이터 전체 초기화
      3. 우선순위 순서(Critical→Major→Normal→Minor)로 정렬해서 재작성
      4. A열 하이퍼링크 + 행 배경색 배치 적용
    """
    sheet_name = f"{version}{SHEET_SUFFIX}"
    print(f"\n[{sheet_name}] 처리 중... (이슈 {len(issues)}개)")

    worksheet = get_or_create_sheet(spreadsheet, sheet_name)
    ensure_header(worksheet)

    if not issues:
        print("  이슈 없음")
        return

    # 우선순위 순서로 정렬 (Critical → Major → Normal → Minor)
    issues = sorted(
        issues,
        key=lambda i: PRIORITY_ORDER.get(i.get('priority', {}).get('name', ''), 99)
    )

    # 기존 QA 데이터 보존: {이슈ID문자열: [QA담당자, QA확인여부]}
    # 이슈 ID(#)는 B열(인덱스 1), QA담당자는 J열(인덱스 9), QA확인여부는 K열(인덱스 10)
    existing_data = worksheet.get_all_values()
    qa_by_id = {
        row[1]: [row[9] if len(row) > 9 else '', row[10] if len(row) > 10 else '']
        for row in existing_data[1:]
        if len(row) > 1 and row[1]
    }

    # 헤더 아래 전체 초기화 (기존 행 수와 새 이슈 수 중 큰 값만큼 클리어)
    clear_end = max(len(existing_data), len(issues) + 1) + 5
    worksheet.batch_clear([f'A2:K{clear_end}'])

    # B~K열 데이터 작성 (A열 링크는 아래 batch_update에서 처리)
    data_rows = [
        issue_to_row(issue) + qa_by_id.get(str(issue['id']), ['', ''])
        for issue in issues
    ]
    worksheet.batch_update([{
        'range':  f'B2:K{1 + len(data_rows)}',
        'values': data_rows,
    }])

    # A열 하이퍼링크 삽입 + 전체 행 배경색을 단일 배치 요청으로 처리
    api_requests = []
    for i, issue in enumerate(issues):
        row_0    = i + 1   # 0-indexed (헤더=0, 첫 번째 데이터=1)
        priority = issue.get('priority', {}).get('name', '')

        api_requests.append(build_hyperlink_request(
            worksheet.id, row_0,
            f"{REDMINE_URL}/issues/{issue['id']}",
        ))
        api_requests.append(build_color_request(
            worksheet.id, row_0,
            PRIORITY_ROW_COLORS.get(priority, PRIORITY_ROW_COLORS['Normal']),
        ))

    spreadsheet.batch_update({'requests': api_requests})
    print(f"  {len(issues)}개 이슈 작성 완료 (링크·행 색상 적용)")


# ==================== 동기화 작업 ====================

def sync_all():
    """전체 동기화 1회 실행 (스케줄러가 주기적으로 호출)"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'=' * 55}")
    print(f"[{now}] 동기화 시작")
    print('=' * 55)

    try:
        # 1단계: 이슈 불러오기
        issues = get_issues()
        print(f"총 {len(issues)}개 이슈 로드 완료")

        # 2단계: 버전별로 이슈 분류 (fixed_version 없으면 '미지정')
        version_bucket = {}
        for issue in issues:
            version = issue.get('fixed_version', {}).get('name', '미지정')
            version_bucket.setdefault(version, []).append(issue)

        print(f"발견된 버전: {list(version_bucket.keys())}")

        # 3단계: Google Sheets 연결
        spreadsheet = connect_spreadsheet()

        # 4단계: 버전별 시트 동기화
        for version, version_issues in version_bucket.items():
            sync_version_sheet(spreadsheet, version, version_issues)

        print(f"\n동기화 완료! 다음 실행: 5분 후")

    except Exception as e:
        # 오류가 발생해도 스케줄러가 멈추지 않도록 예외를 출력만 하고 계속 진행
        print(f"\n[오류] 동기화 중 문제 발생: {e}")


# ==================== 메인 ====================

def main():
    print("=" * 55)
    print("레드마인 이슈 → 구글 스프레드시트 자동 동기화")
    print("실행 주기: 5분마다 | 종료: Ctrl+C")
    print("=" * 55)

    # 시작 즉시 1회 실행
    sync_all()

    # 5분마다 반복 실행 등록
    schedule.every(5).minutes.do(sync_all)

    # 스케줄러 루프 (Ctrl+C로 종료)
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n스케줄러 종료")


if __name__ == '__main__':
    main()
