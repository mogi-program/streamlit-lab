
import base64
import io
import os

import requests
import streamlit as st
from PIL import Image

MAX_SIDE = 1024

# API 주소 설정
try:
    API_URL = st.secrets["API_URL"]
except Exception:
    API_URL = "http://localhost:8000"

# 접근 코드 설정
try:
    ACCESS_CODE = st.secrets["APP_ACCESS_CODE"]
except Exception:
    ACCESS_CODE = ""

st.set_page_config(
    page_title="AI 푸드 도우미",
    page_icon="🍽️",
    layout="centered"
)

st.title("🍽️ AI 푸드 도우미")
st.caption("음식 사진을 업로드하면 AI가 음식 정보를 분석해 줍니다.")

# --------------------------------------------------
# 사진 처리 함수
# --------------------------------------------------

def photo_b64(raw):
    """사진을 긴 쪽 1024px 이하 JPEG로 줄이고 Base64로 변환"""

    image = Image.open(io.BytesIO(raw)).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# --------------------------------------------------
# API 호출 함수
# --------------------------------------------------

def call_api(path, body):
    """FastAPI에 요청하고 JSON 결과 반환"""

    try:
        response = requests.post(
            f"{API_URL}{path}",
            json=body,
            headers={"X-Access-Code": ACCESS_CODE},
            timeout=120
        )

    except requests.RequestException:
        st.error("❌ API 서버에 연결할 수 없습니다.")
        st.caption("API 주소와 Vercel 배포 상태를 확인하세요.")
        return None

    if response.status_code == 200:
        return response.json()

    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = response.text[:100]

    st.error(f"❌ 상태 번호 {response.status_code}: {detail}")
    return None


# --------------------------------------------------
# 분석 결과 출력 함수
# --------------------------------------------------

def display_food_result(data):
    """음식 분석 결과를 화면에 출력"""

    # 음식이 아닌 사진인 경우
    if not data.get("is_food", False):
        st.warning("음식을 인식하지 못했습니다.")
        st.write(data.get("description", "음식 사진을 다시 업로드해 주세요."))
        return

    st.success("음식 분석이 완료되었습니다!")

    # 음식 기본 정보
    st.subheader(f"🍴 {data.get('food_name') or '음식 이름 미확인'}")

    st.write(
        f"**음식 종류:** {data.get('category') or '정보 없음'}"
    )

    st.write(data.get("description", ""))

    # 칼로리 및 가격
    st.divider()
    st.subheader("📊 주요 분석 정보")

    col1, col2 = st.columns(2)

    calories = data.get("calories_kcal")
    price_min = data.get("price_min")
    price_max = data.get("price_max")

    with col1:
        st.metric(
            "예상 칼로리",
            f"{calories:,} kcal" if calories is not None else "정보 없음"
        )

    with col2:
        if price_min is not None and price_max is not None:
            price = f"{price_min:,} ~ {price_max:,}원"
        else:
            price = "정보 없음"

        st.metric("예상 판매 가격", price)

    # 영양 성분
    st.divider()
    st.subheader("🥗 영양 성분")

    nutrition = data.get("nutrition") or {}

    nutrition_items = [
        ("탄수화물", "carbohydrates_g", "g"),
        ("단백질", "protein_g", "g"),
        ("지방", "fat_g", "g"),
        ("나트륨", "sodium_mg", "mg")
    ]

    cols = st.columns(2)

    for index, (name, key, unit) in enumerate(nutrition_items):
        value = nutrition.get(key)

        with cols[index % 2]:
            if value is not None:
                st.metric(name, f"{value:g}{unit}")
            else:
                st.metric(name, "정보 없음")

    # 주요 재료
    st.divider()
    st.subheader("🥕 주요 재료")

    ingredients = data.get("ingredients", [])

    if ingredients:
        st.write(" · ".join(ingredients))
    else:
        st.write("확인된 재료가 없습니다.")

    # 추가 정보
    st.divider()
    st.subheader("📝 추가 정보")

    confidence = data.get("confidence", "미확인")
    notes = data.get("notes", "")

    st.write(f"**분석 신뢰도:** {confidence}")

    if notes:
        st.info(notes)

    st.caption(
        "※ 칼로리, 영양 성분, 가격은 사진을 기반으로 한 AI 추정치입니다."
    )


# --------------------------------------------------
# 메인 화면
# --------------------------------------------------

st.divider()

st.subheader("📷 음식 사진 업로드")

question = st.text_input(
    "분석할 음식에 대한 추가 요청 (선택)",
    placeholder="예: 음식의 칼로리와 주요 재료를 자세히 알려줘."
)

camera = (
    st.camera_input("카메라로 음식 촬영")
    if st.toggle("카메라 사용하기")
    else None
)

upload = st.file_uploader(
    "또는 음식 사진 파일 업로드",
    type=["png", "jpg", "jpeg", "webp"]
)

photo = camera or upload

# 사진 미리보기
if photo is not None:
    st.image(photo, caption="업로드한 음식 사진", width=320)

# 음식 분석 버튼
if st.button(
    "🍽️ 음식 분석하기",
    type="primary",
    use_container_width=True,
    disabled=photo is None
):
    with st.spinner("AI가 음식 사진을 분석하고 있습니다..."):

        body = {
            "image_b64": photo_b64(photo.getvalue()),
            "question": question
        }

        result = call_api("/analyze-food", body)

        if result is not None:
            st.divider()
            display_food_result(result)

# 안내 문구
st.divider()

st.caption(
    "AI 푸드 도우미는 음식 사진을 분석하여 "
    "음식 정보와 예상 영양 성분을 제공합니다."
)
st.caption(
    "※ 사진에 얼굴이나 개인정보가 포함되지 않도록 주의해 주세요."
)
