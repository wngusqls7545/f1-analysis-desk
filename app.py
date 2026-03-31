import streamlit as st
import pandas as pd
import json
import os
import time

# ==========================================
# [0. 폴더 세팅 및 데이터 처리 로직]
# ==========================================
CSV_DIR = "f1_saved_data"
JSON_DIR = "f1_standings"

for d in [CSV_DIR, JSON_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def get_all_years():
    """저장된 JSON 파일들에서 존재하는 모든 연도를 찾아 리스트로 반환"""
    years = set()
    if not os.path.exists(JSON_DIR): return []
    for fname in os.listdir(JSON_DIR):
        if fname.endswith(".json"):
            parts = fname.replace(".json", "").split("_")
            for p in parts:
                if p.isdigit() and len(p) == 4:
                    years.add(int(p))
    return sorted(list(years), reverse=True)

def calculate_standings_by_year(target_year):
    """특정 연도의 데이터만 합산하여 순위 계산"""
    driver_points = {}
    constructor_points = {}
    recent_race_info = None
    max_round = -1

    # 2026 규정: 패스티스트 랩 포인트 제외
    RACE_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
    SPRINT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}

    json_files = [f for f in os.listdir(JSON_DIR) if f.endswith('.json') and str(target_year) in f]
    
    for fname in sorted(json_files):
        try:
            round_num = int(fname.split('_')[0])
            with open(os.path.join(JSON_DIR, fname), 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            is_sprint = "sprint" in fname.lower()
            point_system = SPRINT_POINTS if is_sprint else RACE_POINTS
            
            if not is_sprint and round_num >= max_round:
                max_round = round_num
                recent_race_info = {
                    "winner": data["Drivers"][0]["Driver"]["Name"],
                    "winner_team": data["Drivers"][0]["Team"]["Name"],
                    "track": data.get("TrackName", "Unknown"),
                    "year": target_year,
                    "round": round_num
                }

            for d_record in data["Drivers"]:
                name = d_record["Driver"]["Name"]
                team = d_record["Team"]["Name"]
                pos = d_record["Position"]
                pts = point_system.get(pos, 0)
                driver_points[name] = driver_points.get(name, 0) + pts
                constructor_points[team] = constructor_points.get(team, 0) + pts
        except: continue

    df_d = pd.DataFrame(list(driver_points.items()), columns=['드라이버', 'Points']).sort_values('Points', ascending=False).reset_index(drop=True)
    df_d.index += 1
    df_c = pd.DataFrame(list(constructor_points.items()), columns=['팀', 'Points']).sort_values('Points', ascending=False).reset_index(drop=True)
    df_c.index += 1
    
    return df_d, df_c, recent_race_info

# ==========================================
# [1. 세션 및 테마 설정]
# ==========================================
st.set_page_config(page_title="F1 데이터 분석데스크", layout="wide")

page_names = ["홈", "뉴스", "레이스", "비교", "순위"]
if 'current_page' not in st.session_state: st.session_state.current_page = "홈"

available_years = get_all_years()
if 'view_year' not in st.session_state:
    st.session_state.view_year = available_years[0] if available_years else 2026

# CSS: 정중앙 배치 및 버튼 인식 범위(Padding) 확장
active_idx = page_names.index(st.session_state.current_page) + 1
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0f172a !important; color: #f8fafc !important; }}
    [data-testid="stHeader"] {{ background-color: transparent !important; }}
    .block-container {{ padding-top: 1rem !important; }}

    /* 버튼 스타일: 인식 범위 대폭 확장 (Padding) */
    .stButton > button {{
        background-color: transparent !important;
        border: none !important;
        color: #94a3b8 !important;
        font-size: 22px !important;
        font-weight: 600 !important;
        padding-top: 30px !important;    /* 위쪽 클릭 범위 확대 */
        padding-bottom: 30px !important; /* 아래쪽 클릭 범위 확대 */
        border-radius: 0px !important;
        width: 100% !important;
        transition: 0.3s;
    }}
    .stButton > button:hover {{ color: #ffffff !important; background-color: rgba(255,255,255,0.05) !important; }}
    
    /* 활성화된 메뉴 하단 빨간 밑줄 */
    div[data-testid="column"]:nth-child({active_idx}) button {{
        border-bottom: 4px solid #ef4444 !important;
    }}
    div[data-testid="column"]:nth-child({active_idx}) button p {{
        color: #ef4444 !important;
    }}

    .f1-card {{
        background-color: #1e293b; padding: 20px; border-radius: 12px;
        border-left: 5px solid #ef4444; margin-bottom: 15px;
    }}
    
    /* 중앙 정렬 텍스트 */
    .centered-header {{ text-align: center; margin-bottom: 20px; }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# [2. 상단 네비게이션]
# ==========================================
nav_cols = st.columns(len(page_names))
for i, p in enumerate(page_names):
    with nav_cols[i]:
        # use_container_width=True로 가로 길이 전체를 클릭 범위로 설정
        if st.button(p, use_container_width=True, key=f"nav_{p}"):
            st.session_state.current_page = p
            st.rerun()
st.markdown("<hr style='margin:0; border-color: #1e293b;'>", unsafe_allow_html=True)

# ==========================================
# [3. 사이드바 (업로드 및 연도 선택)]
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png", width=120)
    st.title("⚙️ 분석데스크 설정")
    
    if available_years:
        selected_y = st.selectbox("📅 시즌 선택", available_years, index=available_years.index(st.session_state.view_year))
        if selected_y != st.session_state.view_year:
            st.session_state.view_year = selected_y
            st.rerun()
    
    st.write("---")
    csv_file = st.file_uploader("CSV(텔레메트리) 업로드", type=['csv'])
    if csv_file:
        c_title = st.text_input("데이터 제목")
        if st.button("CSV 저장"):
            with open(os.path.join(CSV_DIR, f"{int(time.time())}_{c_title}.csv"), "wb") as f: f.write(csv_file.getbuffer())
            st.success("CSV 저장 완료!")

    json_file = st.file_uploader("JSON(경기결과) 업로드", type=['json'])
    if json_file:
        j_fname = st.text_input("파일명 (예: 01_race_2026)")
        if st.button("JSON 저장"):
            with open(os.path.join(JSON_DIR, f"{j_fname}.json"), "wb") as f: f.write(json_file.getbuffer())
            st.success("JSON 저장 완료!")
            st.rerun()

# ==========================================
# [4. 페이지 콘텐츠]
# ==========================================
df_d, df_c, recent = calculate_standings_by_year(st.session_state.view_year)

if st.session_state.current_page == "홈":
    # [로고와 제목 정가운데 배치]
    st.markdown("<br>", unsafe_allow_html=True)
    header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
    with header_col2:
        # 로고를 제목 위에 배치
        inner_c1, inner_c2, inner_c3 = st.columns([1, 2, 1])
        with inner_c2:
            st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/1280px-F1.svg.png", use_container_width=True)
        
        st.markdown(f"""
            <div class='centered-header'>
                <h1 style='margin-top:10px;'>F1 데이터 분석데스크</h1>
                <p style='color:#94a3b8; font-size:1.2em;'>{st.session_state.view_year} Season Standings</p>
            </div>
        """, unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)

    # 홈 화면 3분할
    L, R = st.columns([1, 1])
    with L:
        st.subheader("🏆 컨스트럭터 순위")
        st.dataframe(df_c, use_container_width=True, height=250)
        
        st.write("<br>", unsafe_allow_html=True)
        st.subheader("🏁 최근 그랑프리 우승자")
        if recent:
            st.markdown(f"""
                <div class="f1-card">
                    <h2 style='margin:0; color:#ef4444;'>{recent['winner']}</h2>
                    <p style='margin:0; font-size:1.1em;'>{recent['winner_team']}</p>
                    <p style='margin-top:10px; color:#94a3b8;'>📍 {recent['year']} {recent['track']} 그랑프리 (Rd.{recent['round']})</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"{st.session_state.view_year}년 데이터가 없습니다.")

    with R:
        st.subheader("👤 드라이버 순위 (TOP 10)")
        st.dataframe(df_d.head(10), use_container_width=True, height=480)

elif st.session_state.current_page == "레이스":
    st.title("🏎️ 레이스 데이터 목록")
    csv_list = [f for f in os.listdir(CSV_DIR) if f.endswith(".csv")]
    if not csv_list: st.info("데이터가 없습니다.")
    else:
        cols = st.columns(3)
        for i, f in enumerate(csv_list):
            with cols[i%3]:
                st.markdown(f'<div class="f1-card"><h4>{f.split("_", 1)[-1].replace(".csv", "")}</h4></div>', unsafe_allow_html=True)
                if st.button("분석 상세 보기", key=f"btn_{i}", use_container_width=True):
                    st.session_state.selected_df = pd.read_csv(os.path.join(CSV_DIR, f))
                    st.session_state.current_page = "분석상세"
                    st.rerun()

elif st.session_state.current_page == "분석상세":
    if st.button("← 목록으로"): st.session_state.current_page = "레이스"; st.rerun()
    st.dataframe(st.session_state.selected_df, use_container_width=True)

elif st.session_state.current_page in ["뉴스", "비교", "순위"]:
    st.title(f"{st.session_state.current_page}")
    if st.session_state.current_page == "순위":
        st.subheader(f"📊 {st.session_state.view_year} 시즌 전체 드라이버 순위")
        st.table(df_d)