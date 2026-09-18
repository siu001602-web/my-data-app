```python
import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ---------------------------------------------------------
# 1. 기본 설정
# ---------------------------------------------------------

st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide",
)

# KOBIS 일일 박스오피스 API 주소
API_URL = (
    "https://www.kobis.or.kr/kobisopenapi/webservice/rest/"
    "boxoffice/searchDailyBoxOfficeList.json"
)

# 한국 시간대
KST = ZoneInfo("Asia/Seoul")


# ---------------------------------------------------------
# 2. 한국 시간 기준으로 '어제' 날짜 계산
# ---------------------------------------------------------

def get_yesterday():
    """서버의 시간대와 관계없이 한국 시간 기준 어제를 반환합니다."""
    now_kst = datetime.now(KST)
    yesterday = now_kst - timedelta(days=1)

    # KOBIS가 요구하는 YYYYMMDD 형식으로 변환
    return yesterday.strftime("%Y%m%d")


# ---------------------------------------------------------
# 3. KOBIS API 호출
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def get_boxoffice(target_date):
    """
    특정 날짜의 박스오피스 데이터를 가져옵니다.

    ttl=3600:
    같은 날짜를 다시 조회하면 약 1시간 동안
    기존 결과를 재사용해서 API를 다시 호출하지 않습니다.
    """
    try:
        # Streamlit Cloud의 Secrets에서 인증키를 읽습니다.
        # 실제 인증키를 코드에 직접 적지 않습니다.
        api_key = st.secrets["KOBIS_KEY"]

    except Exception:
        return {
            "ok": False,
            "message": (
                "KOBIS_KEY를 찾을 수 없습니다.\n\n"
                "Streamlit Cloud의 앱 설정에서 Secrets에 "
                "`KOBIS_KEY`가 등록되어 있는지 확인하세요."
            ),
        }

    params = {
        "key": api_key,
        "targetDt": target_date,
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=10,
        )

        # HTTP 상태 코드가 정상인지 확인
        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "message": (
                "KOBIS API 요청 시간이 초과되었습니다.\n\n"
                "인터넷 연결이나 KOBIS API 서버 상태를 확인한 뒤 "
                "잠시 후 다시 시도해 주세요."
            ),
        }

    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "message": (
                "KOBIS API에 요청하지 못했습니다.\n\n"
                f"오류 내용: {e}\n\n"
                "인터넷 연결과 KOBIS API 주소가 정상인지 확인해 주세요."
            ),
        }

    except ValueError:
        return {
            "ok": False,
            "message": (
                "KOBIS API가 올바른 JSON 응답을 보내지 않았습니다.\n\n"
                "잠시 후 다시 시도하거나 KOBIS API 상태를 확인해 주세요."
            ),
        }

    # -----------------------------------------------------
    # 4. HTTP 200이어도 faultInfo가 있을 수 있음
    # -----------------------------------------------------

    if "faultInfo" in data:
        fault = data.get("faultInfo", {})

        # faultInfo의 메시지 필드가 있으면 함께 보여줍니다.
        fault_message = (
            fault.get("message")
            or fault.get("message")
            or "KOBIS API에서 오류를 반환했습니다."
        )

        return {
            "ok": False,
            "message": (
                "KOBIS API에서 오류를 반환했습니다.\n\n"
                f"오류 내용: {fault_message}\n\n"
                "특히 Streamlit Secrets의 `KOBIS_KEY`가 "
                "정확한지 확인해 주세요."
            ),
        }

    # 예상한 응답 구조가 있는지 확인
    boxoffice_result = data.get("boxOfficeResult")

    if not boxoffice_result:
        return {
            "ok": False,
            "message": (
                "KOBIS 응답에 `boxOfficeResult`가 없습니다.\n\n"
                "API 응답 형식이나 KOBIS API 상태를 확인해 주세요."
            ),
        }

    movie_list = boxoffice_result.get("dailyBoxOfficeList", [])

    # 영화 목록이 비어 있는 경우
    if not movie_list:
        return {
            "ok": False,
            "message": (
                f"{target_date} 날짜의 박스오피스 영화 목록이 없습니다.\n\n"
                "조회 날짜가 정상적인지, 해당 날짜의 집계 자료가 "
                "KOBIS에 등록되어 있는지 확인해 주세요."
            ),
        }

    return {
        "ok": True,
        "data": movie_list,
    }


# ---------------------------------------------------------
# 5. 문자열로 온 숫자를 숫자로 변환
# ---------------------------------------------------------

def convert_numbers(movie_list):
    """
    KOBIS API의 숫자 값은 문자열로 오기 때문에
    화면에 사용하기 전에 정수로 변환합니다.
    """
    converted = []

    for movie in movie_list:
        item = movie.copy()

        # 정수로 사용할 항목들
        number_fields = [
            "rank",
            "rankInten",
            "audiCnt",
            "audiAcc",
            "scrnCnt",
            "showCnt",
        ]

        for field in number_fields:
            try:
                item[field] = int(item.get(field, 0) or 0)
            except (ValueError, TypeError):
                # 숫자로 변환할 수 없는 값은 0으로 처리
                item[field] = 0

        converted.append(item)

    return converted


# ---------------------------------------------------------
# 6. 제목
# ---------------------------------------------------------

st.title("🎬 어제의 박스오피스")

target_date = get_yesterday()

# 사람이 읽기 좋은 날짜 표시
display_date = datetime.strptime(target_date, "%Y%m%d").strftime(
    "%Y년 %m월 %d일"
)

st.caption(f"한국 시간 기준 조회 날짜: {display_date}")


# ---------------------------------------------------------
# 7. API에서 데이터 가져오기
# ---------------------------------------------------------

result = get_boxoffice(target_date)

if not result["ok"]:
    # API 오류가 있을 때 빈 화면 대신 확인할 사항을 보여줍니다.
    st.error(result["message"])

    st.info(
        """
        **확인할 사항**

        1. Streamlit Cloud → 앱 설정 → Secrets에 `KOBIS_KEY`가 있는지 확인
        2. `KOBIS_KEY` 값에 불필요한 공백이나 따옴표가 없는지 확인
        3. KOBIS API 서버가 정상인지 확인
        4. 해당 날짜의 박스오피스 자료가 실제로 존재하는지 확인
        5. 잠시 후 앱을 새로고침해서 다시 시도
        """
    )

    st.stop()


# ---------------------------------------------------------
# 8. 데이터 변환
# ---------------------------------------------------------

movies = convert_numbers(result["data"])


# ---------------------------------------------------------
# 9. 순위순으로 정렬
# ---------------------------------------------------------

movies.sort(key=lambda movie: movie["rank"])

first_movie = movies[0]


# ---------------------------------------------------------
# 10. 1위 영화의 주요 지표를 크게 표시
# ---------------------------------------------------------

st.subheader(f"🥇 1위: {first_movie['movieNm']}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="어제 관객수",
        value=f"{first_movie['audiCnt']:,}명",
    )

with col2:
    st.metric(
        label="누적 관객수",
        value=f"{first_movie['audiAcc']:,}명",
    )

with col3:
    st.metric(
        label="스크린수",
        value=f"{first_movie['scrnCnt']:,}개",
    )


# ---------------------------------------------------------
# 11. 관객수 상위 5편 막대그래프
# ---------------------------------------------------------

st.subheader("📊 관객수 상위 5편")

top5 = sorted(
    movies,
    key=lambda movie: movie["audiCnt"],
    reverse=True,
)[:5]

# 영화 이름을 인덱스로, 관객수를 값으로 사용
chart_data = {
    movie["movieNm"]: movie["audiCnt"]
    for movie in top5
}

st.bar_chart(chart_data, y_label="관객수", x_label="영화")


# ---------------------------------------------------------
# 12. 전체 박스오피스 표
# ---------------------------------------------------------

st.subheader("📋 전체 박스오피스")

# 표에 보여줄 데이터만 따로 만듭니다.
table_data = []

for movie in movies:
    table_data.append(
        {
            "순위": movie["rank"],
            "영화명": movie["movieNm"],
            "개봉일": movie["openDt"],
            "관객수": movie["audiCnt"],
            "누적관객": movie["audiAcc"],
            "스크린수": movie["scrnCnt"],
        }
    )

st.dataframe(
    table_data,
    use_container_width=True,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn(
            "순위",
            format="%d",
        ),
        "영화명": st.column_config.TextColumn(https://github.com/siu001602-web/my-data-app/tree/main
            "영화명",
        ),
        "개봉일": st.column_config.TextColumn(
            "개봉일",
        ),
        "관객수": st.column_config.NumberColumn(
            "관객수",
            format="%,d",
        ),
        "누적관객": st.column_config.NumberColumn(
            "누적관객",
            format="%,d",
        ),
        "스크린수": st.column_config.NumberColumn(
            "스크린수",
            format="%,d",
        ),
    },
)
```

```text
streamlit
requests
```

Streamlit Cloud에서는 **Settings → Secrets**에 다음처럼 등록하면 됩니다. 실제 키 값은 코드나 `requirements.txt`에 넣지 않습니다.

```toml
KOBIS_KEY = "여기에_발급받은_KOBIS_인증키"
```

핵심적으로 `@st.cache_data(ttl=3600)` 때문에 **같은 날짜의 결과는 약 1시간 동안 재사용**되고, `ZoneInfo("Asia/Seoul")`을 사용해서 배포 서버가 어느 시간대에 있든 **한국 시간 기준 어제**를 조회합니다.
