
from PIL import Image, ImageOps
import streamlit as st
import io
import numpy as np

st.set_page_config(page_title="Grid Collage Maker", page_icon="🧩", layout="wide")

if "bg_color" not in st.session_state:
    st.session_state.bg_color = "#FFFFFF"
if "last_preview" not in st.session_state:
    st.session_state.last_preview = None

st.sidebar.title("🧩 Grid Collage Maker")

files = st.sidebar.file_uploader(
    "이미지 여러 장 업로드 (PNG/JPG/WebP 등)",
    type=["png", "jpg", "jpeg", "webp", "bmp"],
    accept_multiple_files=True,
)

cols = st.sidebar.number_input("세로(Columns)", min_value=1, max_value=20, value=3, step=1)
rows = st.sidebar.number_input("가로(Rows)", min_value=1, max_value=20, value=4, step=1)

cell_w = st.sidebar.number_input("셀 너비(px)", min_value=64, max_value=2000, value=500, step=16)
cell_h = st.sidebar.number_input("셀 높이(px)", min_value=64, max_value=2000, value=700, step=16)

gutter = st.sidebar.number_input("셀 간격(px)", min_value=0, max_value=200, value=24, step=2)
padding = st.sidebar.number_input("바깥 여백(px)", min_value=0, max_value=400, value=48, step=4)
radius = st.sidebar.number_input("모서리 둥글기(px)", min_value=0, max_value=200, value=12, step=2)

st.sidebar.subheader("배경색")
st.sidebar.color_picker("직접 선택(HEX)", key="bg_color")
ref_img_name = None
if files:
    ref_img_name = st.sidebar.selectbox("스포이드 참조 이미지(팔레트 추출)", ["선택 안 함"] + [f.name for f in files])
    if ref_img_name != "선택 안 함":
        pil = None
        for f in files:
            if f.name == ref_img_name:
                pil = Image.open(f).convert("RGB")
                break
        if pil:
            small = pil.resize((64, 64))
            arr = np.array(small).reshape(-1,3)
            uniq, counts = np.unique(arr, axis=0, return_counts=True)
            order = np.argsort(counts)[::-1]
            top = uniq[order][:5]
            st.sidebar.markdown("팔레트에서 선택:")
            pc = st.sidebar.columns(len(top))
            for i, col in enumerate(pc):
                rgb = tuple(int(x) for x in top[i])
                hx = "#%02x%02x%02x" % rgb
                with col:
                    if st.button(" ", key=f"pal_{i}", help=hx):
                        st.session_state.bg_color = hx
                    st.markdown(
                        f'<div style="width:40px;height:24px;border-radius:6px;background:{hx};border:1px solid rgba(0,0,0,.1)"></div>',
                        unsafe_allow_html=True
                    )
st.sidebar.caption("TIP: 참조 이미지를 고르면 상위 색상 팔레트가 나타납니다. 버튼을 눌러 배경색에 적용하세요.")

draw_frame = st.sidebar.checkbox("셀에 흰색 테두리(1px)", value=False)
fit_mode = st.sidebar.selectbox("이미지 맞춤", ["cover (채우기, 일부 잘림)", "contain (여백)"])
order = st.sidebar.selectbox("정렬", ["업로드 순서", "파일명 오름차순", "파일명 내림차순"])
make_preview = st.sidebar.button("🔍 결과 미리보기 생성")
export_btn = st.sidebar.button("🖼️ 콜라주 PNG로 만들기")

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
    return items

def make_collage(images, rows, cols, cell_w, cell_h, gutter, padding, radius, bg_color, draw_frame, fit_mode, progress=None):
    total_slots = rows * cols
    images = images[:total_slots]
    bg = Image.new("RGBA", (cell_w * cols + gutter * (cols - 1) + padding * 2,
                            cell_h * rows + gutter * (rows - 1) + padding * 2), (0,0,0,0))
    if isinstance(bg_color, str) and bg_color.startswith("#"):
        hv = bg_color.lstrip("#")
        r, g, b = tuple(int(hv[i:i+2], 16) for i in (0,2,4))
        bg_rgba = (r,g,b,255)
    else:
        bg_rgba = (255,255,255,255)
    bg_col = Image.new("RGBA", bg.size, bg_rgba)
    bg = Image.alpha_composite(bg_col, bg)

    x0, y0 = padding, padding
    total = max(1, rows * cols)
    i = 0
    for r in range(rows):
        for c in range(cols):
            pct = int(((r*cols + c + 1) / total) * 100)
            if progress: progress.progress(min(pct, 100), text=f"렌더링 중... {pct}%")
            if i >= len(images):
                continue
            name, img = images[i]
            i += 1
            if fit_mode.startswith("cover"):
                img_fit = ImageOps.fit(img, (cell_w, cell_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
            else:
                img_fit = img.copy()
                img_fit.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (cell_w, cell_h), (0,0,0,0))
                ox = (cell_w - img_fit.width) // 2
                oy = (cell_h - img_fit.height) // 2
                canvas.paste(img_fit, (ox, oy))
                img_fit = canvas
            if radius > 0:
                from PIL import ImageDraw
                m = Image.new("L", (cell_w, cell_h), 0)
                d = ImageDraw.Draw(m)
                d.rounded_rectangle([0,0,cell_w,cell_h], radius=radius, fill=255)
                img_fit.putalpha(m)
            if draw_frame:
                from PIL import ImageDraw
                d2 = ImageDraw.Draw(img_fit)
                d2.rounded_rectangle([0.5,0.5,cell_w-0.5,cell_h-0.5], radius=max(0, radius-1), outline="white", width=1)
            bg.alpha_composite(img_fit, (x0 + c*(cell_w+gutter), y0 + r*(cell_h+gutter)))
    if progress: progress.progress(100, text="완료")
    return bg

st.title("✨ 민지 그리드/콜라주 생성긔~")
st.write("여러 이미지를 업로드하고 **행/열 수**를 지정해 미리 보고, **PNG 콜라주**로 내보내세요.")

if not files:
    st.info("왼쪽 사이드바에서 이미지를 업로드해 시작하세요.")
else:
    images = load_images(files)
    images = sort_images(images, order)

    st.subheader("미리보기 (원본 이미지 썸네일)")
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

    st.subheader("📦 결과 미리보기 (콜라주 결과)")
    if make_preview:
        progress = st.progress(0, text="준비 중...")
        collage = make_collage(
            to_show, rows, cols, int(cell_w), int(cell_h),
            int(gutter), int(padding), int(radius),
            st.session_state.bg_color, draw_frame, fit_mode, progress=progress
        )
        st.session_state.last_preview = collage
        progress.empty()

    if st.session_state.last_preview is not None:
        st.image(st.session_state.last_preview, caption="현재 설정으로 생성된 콜라주", use_column_width=True)

    if export_btn:
        progress = st.progress(0, text="콜라주 생성 중...")
        collage = make_collage(
            to_show, rows, cols, int(cell_w), int(cell_h),
            int(gutter), int(padding), int(radius),
            st.session_state.bg_color, draw_frame, fit_mode, progress=progress
        )
        st.session_state.last_preview = collage
        buf = io.BytesIO()
        collage.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        progress.empty()
        st.success("콜라주가 생성되었습니다. 아래에서 바로 확인/다운로드 하세요.")
        st.image(collage, caption="생성된 콜라주", use_column_width=True)
        st.download_button(
            "📥 PNG 다운로드",
            data=buf,
            file_name="collage.png",
            mime="image/png"
        )
