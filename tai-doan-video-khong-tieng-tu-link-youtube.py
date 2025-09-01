import streamlit as st
import yt_dlp
import os
import subprocess
import tkinter as tk
from tkinter import filedialog

# --- Hàm chọn thư mục ---
def pick_directory():
    root = tk.Tk()
    root.withdraw()
    folder = filedialog.askdirectory()
    root.destroy()
    return folder

# --- Hàm tải và cắt theo số phút đã chọn ---
def download_segment(url, save_dir, minutes, mode="video", resolution=None, filename="output", crf=23, preset="veryfast"):
    os.makedirs(save_dir, exist_ok=True)
    temp_file = os.path.join(save_dir, f"{filename}_temp.%(ext)s")
    final_file = os.path.join(save_dir, f"{filename}.mp4" if mode != "audio" else f"{filename}.mp3")

    if mode == "audio":
        fmt = "bestaudio/best"
    elif mode == "mute":
        fmt = f"bestvideo[height<={resolution}]" if resolution else "bestvideo"
    else:  # video có tiếng
        fmt = f"bestvideo[height<={resolution}]+bestaudio/best" if resolution else "bestvideo+bestaudio/best"

    ydl_opts = {
        "format": fmt,
        "outtmpl": temp_file,
        "merge_output_format": "mp4" if mode != "audio" else "mp3"
    }

    # tải video gốc
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # tìm file vừa tải
    downloaded_file = None
    for f in os.listdir(save_dir):
        if f.startswith(f"{filename}_temp"):
            downloaded_file = os.path.join(save_dir, f)
            break

    if not downloaded_file:
        st.error("❌ Không tìm thấy file sau khi tải!")
        return

    # số giây cần cắt
    duration_sec = minutes * 60

    # cắt video/audio
    if mode == "audio":
        cmd = ["ffmpeg", "-y", "-i", downloaded_file, "-t", str(duration_sec), "-vn", "-acodec", "mp3", final_file]
    elif mode == "mute":
        cmd = ["ffmpeg", "-y", "-i", downloaded_file, "-t", str(duration_sec), "-an", "-c:v", "libx264", "-preset", preset, "-crf", str(crf), final_file]
    else:  # video có tiếng
        cmd = ["ffmpeg", "-y", "-i", downloaded_file, "-t", str(duration_sec), "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-c:a", "aac", "-b:a", "128k", final_file]

    subprocess.run(cmd, check=True)

    # xoá file gốc
    os.remove(downloaded_file)
    st.success(f"✅ Đã lưu {final_file}")

# --- Giao diện Streamlit ---
st.title("🎬 YouTube Downloader (tải theo số phút đầu)")

if "save_dir" not in st.session_state:
    st.session_state["save_dir"] = os.getcwd()
if "duration" not in st.session_state:
    st.session_state["duration"] = 9   # mặc định 9 phút

if st.button("📂 Chọn thư mục lưu file"):
    folder = pick_directory()
    if folder:
        st.session_state["save_dir"] = folder

st.write(f"📁 Thư mục lưu hiện tại: `{st.session_state['save_dir']}`")

# nhập link
links_text = st.text_area("📌 Dán link YouTube (mỗi dòng một link):")

# tăng/giảm số phút
col1, col2, col3 = st.columns([1,2,1])
with col1:
    if st.button("➖"):
        if st.session_state.duration > 1:
            st.session_state.duration -= 1
with col2:
    st.markdown(f"<h4 style='text-align:center'>Thời lượng tải: {st.session_state.duration} phút</h4>", unsafe_allow_html=True)
with col3:
    if st.button("➕"):
        st.session_state.duration += 1

# tuỳ chỉnh encode
st.markdown("### ⚙️ Tuỳ chỉnh encode H.264")
crf = st.slider("CRF (0-51, thấp = đẹp hơn nhưng nặng)", min_value=18, max_value=30, value=23)
preset = st.selectbox("Preset", 
    ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"], 
    index=2)

# lấy danh sách video
if st.button("🔎 Lấy danh sách video"):
    links = [l.strip() for l in links_text.splitlines() if l.strip()]
    st.session_state["videos"] = [{"idx": i+1, "url": link} for i, link in enumerate(links)]

# hiển thị danh sách video
if "videos" in st.session_state:
    for vid in st.session_state["videos"]:
        st.subheader(f"Video {vid['idx']}: {vid['url']}")

        resolution = st.selectbox(
            f"Độ phân giải cho Video {vid['idx']}:",
            ["360", "480", "720", "1080"],
            key=f"res_{vid['idx']}"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(f"⬇️ MP3 ({st.session_state.duration} phút)", key=f"mp3_{vid['idx']}"):
                download_segment(vid["url"], st.session_state["save_dir"],
                                 st.session_state.duration,
                                 mode="audio", filename=f"Video{vid['idx']}",
                                 crf=crf, preset=preset)
        with col2:
            if st.button(f"🎥 Có tiếng ({st.session_state.duration} phút)", key=f"video_{vid['idx']}"):
                download_segment(vid["url"], st.session_state["save_dir"],
                                 st.session_state.duration,
                                 mode="video", resolution=resolution,
                                 filename=f"Video{vid['idx']}",
                                 crf=crf, preset=preset)
        with col3:
            if st.button(f"🔇 Không tiếng ({st.session_state.duration} phút)", key=f"mute_{vid['idx']}"):
                download_segment(vid["url"], st.session_state["save_dir"],
                                 st.session_state.duration,
                                 mode="mute", resolution=resolution,
                                 filename=f"Video{vid['idx']}",
                                 crf=crf, preset=preset)

    # 🔥 Thêm nút tải tất cả (mặc định 720p, không tiếng)
    if st.button(f"📥 Tải tất cả ({st.session_state.duration} phút, không tiếng, 720p)"):
        for vid in st.session_state["videos"]:
            with st.spinner(f"Đang tải Video {vid['idx']} ..."):
                download_segment(
                    vid["url"],
                    st.session_state["save_dir"],
                    st.session_state.duration,
                    mode="mute",
                    resolution="720",   # mặc định 720p
                    filename=f"Video{vid['idx']}",
                    crf=crf,
                    preset=preset
                )
        st.success("✅ Đã tải xong tất cả video ở chế độ không tiếng (720p)!")
