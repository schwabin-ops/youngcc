
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 페이지 기본 설정
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide"
)

# 따뜻한 색감의 화면 디자인
st.markdown("""
<style>
.stApp {
    background-color: #FFF9F2;
}
h1, h2, h3, p, label {
    color: #543D32;
}
div[data-baseweb="select"] {
    background-color: #FFFFFF;
}
</style>
""", unsafe_allow_html=True)

st.title("🏘️ 동네별 인구 피라미드")
st.caption("전국 읍·면·동의 연령별 남녀 인구를 확인해 보세요.")

# 원본 ZIP CSV를 직접 읽고, 데이터를 캐시에 저장해 반복 다운로드 방지
DATA_URL = (
    "https://raw.githubusercontent.com//schwabin-ops/youngcc/"
    "main/population_ts_yearly_gender.zip"
)

@st.cache_data(show_spinner="전국 인구 데이터를 불러오는 중입니다...")
def load_data():
    # 압축 파일을 별도로 다운로드하거나 풀지 않고 판다스로 읽기
    errors = []
    for encoding in ["utf-8-sig", "cp949", "euc-kr"]:
        try:
            df = pd.read_csv(
                DATA_URL,
                compression="zip",
                encoding=encoding,
                low_memory=False
            )
            break
        except UnicodeDecodeError as e:
            errors.append(e)
    else:
        raise errors[-1]

    # 열 이름의 앞뒤 공백 제거
    df.columns = df.columns.astype(str).str.strip()

    # 연도 열을 숫자로 변환해 가장 최신 연도만 남기기
    if "연도" not in df.columns:
        raise ValueError(
            f"'연도' 열을 찾을 수 없습니다. 실제 열: {list(df.columns[:10])}"
        )

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"]).copy()
    df["연도"] = df["연도"].astype(int)
    latest_year = int(df["연도"].max())
    df = df[df["연도"] == latest_year].copy()

    # 지역명 열을 문자열로 통일
    for col in ["시도", "시군구", "동"]:
        if col not in df.columns:
            raise ValueError(f"필수 열 '{col}'을 찾을 수 없습니다.")
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df, latest_year


try:
    df, latest_year = load_data()
except Exception as e:
    st.error("인구 데이터를 불러오지 못했습니다.")
    st.exception(e)
    st.stop()

# 0세부터 100세 이상까지 나이 라벨을 순서대로 생성
ages = [f"{age}세" for age in range(101)]
ages[-1] = "100세 이상"

# 데이터에 필요한 연령별 남녀 열이 모두 있는지 확인
male_cols = [f"남_{age}" for age in ages]
female_cols = [f"여_{age}" for age in ages]
age_cols = male_cols + female_cols

missing_cols = [col for col in age_cols if col not in df.columns]

if missing_cols:
    st.error(
        "연령별 인구 열을 찾을 수 없습니다. "
        f"누락된 열 예시: {missing_cols[:10]}"
    )
    st.stop()

# 지역 선택에 필요한 고유 목록을 정렬
provinces = sorted(df["시도"].unique().tolist())

if not provinces:
    st.warning("선택할 수 있는 시도 데이터가 없습니다.")
    st.stop()

# 시도 → 시군구 → 동 순서로 선택
st.subheader(f"📍 지역 선택 · {latest_year}년")

col1, col2, col3 = st.columns(3)

with col1:
    selected_province = st.selectbox("① 시도", provinces)

province_df = df[df["시도"] == selected_province]

districts = sorted(province_df["시군구"].unique().tolist())

with col2:
    selected_district = st.selectbox("② 시군구", districts)

district_df = province_df[
    province_df["시군구"] == selected_district
]

neighborhoods = sorted(district_df["동"].unique().tolist())

with col3:
    selected_neighborhood = st.selectbox("③ 동", neighborhoods)

# 선택한 지역의 인구 자료만 추출
selected_df = district_df[
    district_df["동"] == selected_neighborhood
].copy()

if selected_df.empty:
    st.warning("선택한 지역의 인구 데이터가 없습니다.")
    st.stop()

# 숫자 열에 쉼표가 있거나 값이 비어 있어도 계산할 수 있도록 정리
for col in age_cols:
    selected_df[col] = pd.to_numeric(
        selected_df[col].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    ).fillna(0)

# 같은 지역에 행이 여러 개 있으면 연령별 인구를 합산
population = selected_df[age_cols].sum()

male_population = [float(population[col]) for col in male_cols]
female_population = [float(population[col]) for col in female_cols]

# 남자는 음수로 바꿔 왼쪽에, 여자는 양수로 오른쪽에 표시
male_values = [-value for value in male_population]
female_values = female_population

# 전체 인구와 성별 인구 계산
total_male = sum(male_population)
total_female = sum(female_population)
total_population = total_male + total_female

# 주요 수치 표시
st.divider()
st.subheader(
    f"📊 {selected_province} {selected_district} "
    f"{selected_neighborhood} 인구 현황"
)

metric1, metric2, metric3 = st.columns(3)
metric1.metric("전체 인구", f"{total_population:,.0f}명")
metric2.metric("남자 인구", f"{total_male:,.0f}명")
metric3.metric("여자 인구", f"{total_female:,.0f}명")

# Plotly 가로 막대그래프 생성
fig = go.Figure()

fig.add_trace(go.Bar(
    name="남자",
    y=ages,
    x=male_values,
    orientation="h",
    marker_color="#D98970",
    hovertemplate="나이: %{y}<br>남자: %{customdata:,.0f}명<extra></extra>",
    customdata=male_population
))

fig.add_trace(go.Bar(
    name="여자",
    y=ages,
    x=female_values,
    orientation="h",
    marker_color="#E8B85C",
    hovertemplate="나이: %{y}<br>여자: %{x:,.0f}명<extra></extra>"
))

# 좌우 축의 범위를 대칭으로 만들어 비교하기 쉽게 설정
max_population = max(
    max(male_population, default=0),
    max(female_population, default=0),
    1
)
axis_limit = max_population * 1.12

# 축 눈금은 음수 대신 양수 인구수로 표시
tick_count = 5
tick_step = axis_limit / tick_count
tickvals = [
    -axis_limit + i * (2 * axis_limit / (tick_count * 2))
    for i in range(tick_count * 2 + 1)
]
ticktext = [f"{abs(value):,.0f}" for value in tickvals]

fig.update_layout(
    title={
        "text": f"{selected_neighborhood} 연령별 인구 피라미드 ({latest_year}년)",
        "x": 0.5,
        "xanchor": "center"
    },
    barmode="overlay",
    bargap=0.12,
    height=1000,
    paper_bgcolor="#FFF9F2",
    plot_bgcolor="#FFF9F2",
    font=dict(family="Malgun Gothic, sans-serif", color="#543D32"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5
    ),
    xaxis=dict(
        title="인구수 (명)",
        range=[-axis_limit, axis_limit],
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor="#A78B78",
        gridcolor="#EADFD4"
    ),
    yaxis=dict(
        title="나이",
        type="category",
        categoryorder="array",
        categoryarray=ages,
        autorange="normal",
        tickmode="array",
        tickvals=ages,
        ticktext=ages,
        showgrid=False
    ),
    margin=dict(l=90, r=45, t=100, b=65)
)

# 완성된 그래프 출력
st.plotly_chart(fig, use_container_width=True)

# 축 순서를 확인할 수 있도록 안내
st.caption(
    "※ 세로축 확인: 맨 아래 0세 · 맨 위 100세 이상. "
    "남자는 왼쪽, 여자는 오른쪽에 표시됩니다."
)

# 원본 데이터 확인 기능
with st.expander("🔎 선택한 지역의 연령별 인구표 보기"):
    result_table = pd.DataFrame({
        "나이": ages,
        "남자 인구": male_population,
        "여자 인구": female_population
    })
    result_table["전체 인구"] = (
        result_table["남자 인구"] + result_table["여자 인구"]
    )
    st.dataframe(result_table, use_container_width=True, hide_index=True)

st.caption("데이터 출처: GitHub의 전국 읍·면·동 연도별 성별 인구 ZIP 파일")
