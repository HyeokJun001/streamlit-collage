
from PIL import Image, ImageOps
import streamlit as st
import io

st.set_page_config(page_title="Grid Collage Maker", page_icon="🧩", layout="wide")

# =============== Sidebar Controls ===============
st.sidebar.title("🧩 Grid Collage Maker")

files = st.sidebar.file_uploader(
    "이미지 여러 장 업로드 (PNG/JPG/WebP 등)",
    type=["png", "jpg", "jpeg", "webp", "bmp"],
    accept_multiple_files=True,
)

cols = st.sidebar.number_input("열(Columns)", min_value=1, max_value=20, value=5, step=1)
rows = st.sidebar.number_input("행(Rows)", min_value=1, max_value=20, value=4, step=1)

cell_w = st.sidebar.number_input("셀 너비(px)", min_value=64, max_value=2000, value=512, step=16)
cell_h = st.sidebar.number_input("셀 높이(px)", min_value=64, max_value=2000, value=512, step=16)

gutter = st.sidebar.number_input("셀 간격(px)", min_value=0, max_value=200, value=24, step=2)
padding = st.sidebar.number_input("바깥 여백(px)", min_value=0, max_value=400, value=48, step=4)
radius = st.sidebar.number_input("모서리 둥글기(px)", min_value=0, max_value=200, value=12, step=2)

bg_color = st.sidebar.color_picker("배경색", "#FFFFFF")
draw_frame = st.sidebar.checkbox("셀에 흰색 테두리(1px)", value=False)
fit_mode = st.sidebar.selectbox("이미지 맞춤", ["cover (채우기, 일부 잘림)", "contain (여백)"])

order = st.sidebar.selectbox("정렬", ["업로드 순서", "파일명 오름차순", "파일명 내림차순"])

export_btn = st.sidebar.button("🖼️ 콜라주 PNG로 만들기")

st.sidebar.caption("Tip: 열, 행 수를 바꾸면 자동으로 미리보기 레이아웃이 바뀝니다.")

# =============== Helper Functions ===============
def load_images(files):
    imgs = []
    for f in files:
        try:
            img = Image.open(f).convert("RGBA")
            imgs.append((f.name, img))
        except Exception:
            continue
    return imgs

def sort_images(items, mode):
    if mode == "파일명 오름차순":
        return sorted(items, key=lambda x: x[0])
    if mode == "파일명 내림차순":
        return sorted(items, key=lambda x: x[0], reverse=True)
    return items  # 업로드 순서

def make_collage(images, rows, cols, cell_w, cell_h, gutter, padding, radius, bg_color, draw_frame, fit_mode):
    total_slots = rows * cols
    images = images[:total_slots]  # 초과 이미지 컷
    bg = Image.new("RGBA", (cell_w * cols + gutter * (cols - 1) + padding * 2,
                            cell_h * rows + gutter * (rows - 1) + padding * 2), (0,0,0,0))
    # 배경색 적용
    bg_col = Image.new("RGBA", bg.size, Image.new("RGBA", (1,1), bg_color).getpixel((0,0)))
    bg = Image.alpha_composite(bg_col, bg)

    # 셀 그리기
    x0, y0 = padding, padding
    i = 0
    for r in range(rows):
        for c in range(cols):
            if i >= len(images):
                break
            name, img = images[i]
            i += 1

            # Resize
            if fit_mode.startswith("cover"):
                # cover: 채우기 — 중앙 크롭
                img_fit = ImageOps.fit(img, (cell_w, cell_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            else:
                # contain: 짧은 변 기준으로 축소 후 여백
                img_fit = img.copy()
                img_fit.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (cell_w, cell_h), (0,0,0,0))
                ox = (cell_w - img_fit.width) // 2
                oy = (cell_h - img_fit.height) // 2
                canvas.paste(img_fit, (ox, oy))
                img_fit = canvas

            # 모서리 둥글기
            if radius > 0:
                from PIL import ImageDraw
                m = Image.new("L", (cell_w, cell_h), 0)
                d = ImageDraw.Draw(m)
                d.rounded_rectangle([0,0,cell_w,cell_h], radius=radius, fill=255)
                img_fit.putalpha(m)

            # 프레임(흰색 1px)
            if draw_frame:
                from PIL import ImageDraw
                d2 = ImageDraw.Draw(img_fit)
                d2.rounded_rectangle([0.5,0.5,cell_w-0.5,cell_h-0.5], radius=max(0, radius-1), outline="white", width=1)

            bg.alpha_composite(img_fit, (x0 + c*(cell_w+gutter), y0 + r*(cell_h+gutter)))

    return bg

# =============== Preview ===============
st.title("✨ 이미지 그리드/콜라주 생성기")
st.write("여러 이미지를 업로드하고 **행/열 수**를 지정해 미리 보고, **PNG 콜라주**로 내보내세요.")

if not files:
    st.info("왼쪽 사이드바에서 이미지를 업로드해 시작하세요.")
else:
    images = load_images(files)
    images = sort_images(images, order)

    # Preview as a responsive grid using Streamlit columns
    st.subheader("미리보기")
    total_slots = rows * cols
    to_show = images[:total_slots]
    idx = 0
    for r in range(rows):
        columns = st.columns(cols, gap="small")
        for c in range(cols):
            if idx >= len(to_show):
                columns[c].empty()
                continue
            name, img = to_show[idx]
            idx += 1
            with columns[c]:
                st.image(img, caption=name, use_column_width=True)

    if export_btn:
        collage = make_collage(
            to_show, rows, cols, int(cell_w), int(cell_h),
            int(gutter), int(padding), int(radius),
            bg_color, draw_frame, fit_mode
        )
        buf = io.BytesIO()
        collage.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        st.success("콜라주가 생성되었습니다. 아래에서 다운로드하세요.")
        st.download_button(
            "📥 PNG 다운로드",
            data=buf,
            file_name="collage.png",
            mime="image/png"
        )
