import json
from flask import Flask, request, jsonify
import instaloader
import re
import os
import subprocess
import shutil
import time
import platform
from videoCaptioner import add_caption_to_video
from postToFacebook import auto_post_from_folder
from post_comment import post_comment_with_image,post_comment
from videoUpscale import upscale_video
from getFacebookPhoto import download_facebook_images
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from postToYoutube import upload_youtube_video
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


app = Flask(__name__)
L = instaloader.Instaloader(dirname_pattern="downloaded")
L = instaloader.Instaloader()
try:
    L.login("AlphonseMcClouds", "#Everfree99")
    print("Login successful!")
except instaloader.exceptions.BadCredentialsException as e:
    print(f"Login failed: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

def find_ffmpeg_path():
    """
    ค้นหา path ของ ffmpeg โดยอัตโนมัติ ขึ้นอยู่กับระบบปฏิบัติการ
    ตรวจสอบ Windows, Ubuntu, และ Raspberry Pi (ซึ่งเป็น Linux เหมือนกัน)
    Returns:
        str: Path ไปยัง ffmpeg executable, หรือ None ถ้าไม่พบ
    """
    system_os = platform.system()
    ffmpeg_path = None

    if system_os == "Windows":
        # สำหรับ Windows, ลอง path ที่กำหนดไว้ก่อน
        windows_default_path = "C:/ffmpeg/bin/ffmpeg.exe"
        if os.path.exists(windows_default_path):
            ffmpeg_path = windows_default_path
            print(f"พบ ffmpeg ที่ path เริ่มต้นของ Windows: {ffmpeg_path}")
        else:
            # ถ้าไม่พบที่ path เริ่มต้น, ลองค้นหาใน PATH
            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                print(f"พบ ffmpeg ใน PATH ของ Windows: {ffmpeg_path}")
            else:
                print("ไม่พบ ffmpeg ใน PATH หรือที่ C:/ffmpeg/bin/ffmpeg.exe บน Windows")
    elif system_os == "Linux":
        # สำหรับ Linux (รวมถึง Ubuntu และ Raspberry Pi)
        # ค้นหาใน PATH เป็นหลัก
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            # สามารถตรวจสอบเพิ่มเติมสำหรับ Raspberry Pi ได้หากต้องการ
            # เช่น ตรวจสอบ release file: if "Raspbian" in platform.version():
            print(f"พบ ffmpeg ใน PATH ของ Linux (Ubuntu/Raspberry Pi): {ffmpeg_path}")
        else:
            print("ไม่พบ ffmpeg ใน PATH บน Linux (Ubuntu/Raspberry Pi)")
    else:
        print(f"ระบบปฏิบัติการที่ไม่รู้จัก: {system_os}. พยายามค้นหา ffmpeg ใน PATH")
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            print(f"พบ ffmpeg ใน PATH ของระบบปฏิบัติการที่ไม่รู้จัก: {ffmpeg_path}")
        else:
            print(f"ไม่พบ ffmpeg ใน PATH ของระบบปฏิบัติการที่ไม่รู้จัก: {system_os}")

    return ffmpeg_path

# กำหนด FFMPEG_PATH โดยเรียกใช้ฟังก์ชันค้นหาอัตโนมัติ
FFMPEG_PATH = find_ffmpeg_path()

if not FFMPEG_PATH:
    print("คำเตือน: ไม่พบ ffmpeg ในระบบ โปรดตรวจสอบว่าได้ติดตั้งและอยู่ใน PATH แล้ว")
    # คุณอาจต้องการเพิ่มการจัดการข้อผิดพลาดที่นี่ เช่น:
    # raise FileNotFoundError("FFmpeg executable not found. Please install FFmpeg.")
else:
    print(f"FFMPEG_PATH ที่ใช้งาน: {FFMPEG_PATH}")

def get_final_url_with_selenium(url):
    """ใช้ Selenium เพื่อดึง URL สุดท้ายหลังจาก redirect"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    final_url = driver.current_url
    driver.quit()
    return final_url

def download_video_yt_dlp(url, output_path="download/download.mp4"):
    """ดาวน์โหลดวิดีโอด้วย yt-dlp พร้อมดึง title และรวมเสียง/วิดีโอด้วย FFmpeg"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if os.path.exists(output_path):
            print(f"กำลังลบไฟล์เก่า: {output_path}")
            os.remove(output_path)

        # Step 1: ดึง title ก่อน
        get_title_cmd = ['yt-dlp', '--get-title', url]
        title_result = subprocess.run(get_title_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        title = title_result.stdout.strip() if title_result.returncode == 0 else None

        # Step 2: ดาวน์โหลดวิดีโอ
        command = [
            'yt-dlp',
            '-f', 'bv*+ba[ext=m4a]/b[ext=mp4]',
            url,
            '-o', output_path,
            '--merge-output-format', 'mp4',
            '--ffmpeg-location', FFMPEG_PATH,
            '--remux-video', 'mp4'
        ]

        print(f"ดาวน์โหลดจาก: {url}")
        print(f"บันทึกเป็น: {output_path}")
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if process.returncode == 0:
            print("✅ ดาวน์โหลดสำเร็จ")
            return output_path, None, title
        else:
            print("❌ ดาวน์โหลดล้มเหลว")
            return None, process.stderr, title

    except Exception as e:
        return None, str(e), None

def download_image_or_album(url, output_dir="downloaded", single_photo=False):
    """ดาวน์โหลดรูปภาพหรืออัลบั้มด้วย gallery-dl โดยไม่สร้างโฟลเดอร์ย่อย"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        # กำหนด output template ให้เป็นชื่อไฟล์อย่างเดียว
        # {file.name} คือ placeholder สำหรับชื่อไฟล์เดิม
        os.makedirs(output_dir, exist_ok=True)
        output_template = "{filename}.{extension}"  # รวมนามสกุลไฟล์
        command = ['gallery-dl', '-q', '-D', output_dir, '-f', output_template]
        if single_photo:
            command.extend(['--range', '1']) # ดาวน์โหลดเฉพาะไฟล์แรก
        command.append(url)

        print(f"กำลังดาวน์โหลดด้วย gallery-dl จาก: {url}")
        print(f"บันทึกไว้ที่: {output_dir} (โดยไม่สร้างโฟลเดอร์ย่อย)")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print("ดาวน์โหลดสำเร็จ!")
            return output_dir, None
        else:
            error_message = stderr.decode('utf-8')
            print(f"เกิดข้อผิดพลาดในการดาวน์โหลดด้วย gallery-dl: {error_message}")
            return None, f"เกิดข้อผิดพลาดในการดาวน์โหลดรูปภาพ: {error_message}"

    except FileNotFoundError:
        error_message = "Error: ไม่พบคำสั่ง gallery-dl โปรดตรวจสอบให้แน่ใจว่าได้ติดตั้ง gallery-dl แล้ว"
        print(error_message)
        return None, error_message
    except Exception as e:
        error_message = f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}"
        print(error_message)
        return None, error_message


def download_instagram_item(url, output_dir="downloaded"):
    """ดาวน์โหลดโพสต์ Instagram (รูปภาพหรือวิดีโอ)"""
    shortcode = extract_instagram_shortcode(url)
    print("กำลังดาวน์โหลดด้วย shortcode:", shortcode)
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        print("ดึงโพสต์สำเร็จ, เริ่มดาวน์โหลด")
        L.download_post(post, target=shortcode)

        video_path = None  # เก็บ path ของวิดีโอ (ถ้ามี)
        image_path = None  # เก็บ path ของรูปภาพ (ถ้ามี)

        for f in os.listdir(output_dir):
            lower_f = f.lower()
            if lower_f.endswith(".mp4"):
                print("พบไฟล์วิดีโอ:", f)
                video_path = os.path.join(output_dir, f)
                break  # เจอวิดีโอแล้วออกเลย (ยึดวิดีโอเป็นหลัก)
            elif lower_f.endswith((".jpg", ".jpeg", ".png")):
                print("พบไฟล์รูปภาพ:", f)
                image_path = os.path.join(output_dir, f)

        if video_path:
            return video_path, post.caption  # คืนค่าวิดีโอและแคปชั่น (ถ้ามี)
        elif image_path:
            return image_path, post.caption  # คืนค่ารูปภาพและแคปชั่น (ถ้าไม่มีวิดีโอ)
        else:
            return None, "ไม่พบไฟล์ที่ดาวน์โหลดจาก Instagram"

    except Exception as e:
        print("เกิดข้อผิดพลาดในการดาวน์โหลด:", e)
        return None, f"เกิดข้อผิดพลาดในการดาวน์โหลดวิดีโอ Instagram: {e}"

def extract_instagram_shortcode(url):
    """แยก shortcode จาก URL Instagram"""
    clean_url = url.split('?')[0]
    match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]{5,})', clean_url)
    return match.group(1) if match else None

def is_instagram_url(url):
    """ตรวจสอบว่าเป็น URL Instagram"""
    return "instagram.com" in url

def clear_download_folder(folder_path):
    """ลบไฟล์และโฟลเดอร์ทั้งหมดใน directory ที่ระบุ"""
    try:
        if os.path.exists(folder_path):
            print(f"กำลังล้างโฟลเดอร์: {folder_path}")
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    print(f"ลบไฟล์: {item_path}")
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"ลบโฟลเดอร์: {item_path}")
            print(f"ล้างโฟลเดอร์ {folder_path} สำเร็จ.")
        else:
            print(f"โฟลเดอร์ {folder_path} ไม่พบ.")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการล้างโฟลเดอร์ {folder_path}: {e}")

@app.route('/fetch', methods=['POST'])
def download_content():
    clear_download_folder("downloaded")
    data = request.get_json()
    if not data or 'url' not in data or 'access_token' not in data or 'page_id' not in data:
        return jsonify({"error": "Missing 'url', 'access_token', or 'page_id' in request body"}), 400

    target_url = data['url']
    access_token = data['access_token']
    page_id = data['page_id']
    download_folder = "downloaded"
    os.makedirs(download_folder, exist_ok=True)
    video_caption_text = data.get("videoCaption")
    description = data.get("description", "")
    filepath = None
    error = None
    success = False
    reel_id = None
    media_ids = []  # เก็บ ID ของ media ที่อัปโหลด (ใช้กับอัลบั้ม)
    youtube_upload_enabled = data.get("youtube", "no").lower() == "yes"
    youtube_channel_id = data.get("channelid") # Note: channelid is often not directly used for user uploads via OAuth

    try:
        result = None  # <-- เตรียมตัวแปรไว้ก่อน
        instagram_caption = None
        # youtube_title ถูกประกาศและใช้งานในภายหลังเมื่อเรียก download_video_yt_dlp
        youtube_title = None  # เตรียมตัวแปรสำหรับเก็บ title จาก YouTube

        if is_instagram_url(target_url):
            print("ตรวจพบ URL Instagram...")
            filepath, error = download_instagram_item(target_url, download_folder)
            print(f"ไฟล์ที่ดาวน์โหลดจาก Instagram: {filepath}")
            if filepath and filepath.lower().endswith(('.mp4')):
                # เรียก upscale_video หากเป็นวิดีโอ
                upscaled_video_path = upscale_video(filepath)
                if upscaled_video_path:
                    print(f"วิดีโอถูก upscale แล้ว: {upscaled_video_path}")
                    # แทนที่ filepath ด้วย path ของวิดีโอที่ถูก upscale
                    filepath = upscaled_video_path
                # เรียก add_caption_to_video หลังจาก upscale
                if video_caption_text:
                    captioned_video_path = add_caption_to_video(filepath, video_caption_text)
                    if captioned_video_path:
                        print(f"วิดีโอถูกใส่แคปชันแล้ว: {captioned_video_path}")
                        # แทนที่ filepath ด้วย path ของวิดีโอที่ใส่แคปชัน
                        filepath = captioned_video_path
                    else:
                        print("การใส่แคปชันวิดีโอไม่สำเร็จ จะโพสต์วิดีโอต้นฉบับแทน")
            description = data.get("caption") or instagram_caption or ""
            result = auto_post_from_folder(access_token, page_id, download_folder, description)

        elif "facebook.com" in target_url:
            print("ตรวจพบ URL Facebook...")
            original_target_url = target_url # เก็บ URL เดิมไว้เผื่อ Selenium ไม่สำเร็จ

            # Check for the specific Facebook share URL pattern
            if "facebook.com/share/" in target_url:
                print("URL matches Facebook share pattern. ใช้ Selenium เพื่อดึง URL จริง")
                try:
                    target_url = get_final_url_with_selenium(target_url)
                    print(f"URL หลัง redirect จาก Selenium: {target_url}")
                except Exception as e:
                    print(f"เกิดข้อผิดพลาดในการดึง URL สุดท้ายด้วย Selenium: {e}. จะพยายามใช้ URL เดิม: {original_target_url}")
                    target_url = original_target_url # กลับไปใช้ URL เดิมถ้า Selenium ล้มเหลว

            # ตรวจสอบและปรับปรุง URL ของ Facebook photo ให้เหลือเฉพาะ fbid
            if "/photo/" in target_url:
                try:
                    parsed_url = urlparse(target_url)
                    query_params = parse_qs(parsed_url.query)

                    if 'fbid' in query_params:
                        # สร้าง query string ใหม่ที่มีเฉพาะ fbid
                        new_query_params = {'fbid': query_params['fbid']}
                        new_query_string = urlencode(new_query_params, doseq=True)
                        
                        # สร้าง URL ใหม่จากส่วนต่างๆ และ query string ที่ปรับปรุงแล้ว
                        new_url_parts = list(parsed_url)
                        new_url_parts[4] = new_query_string # index 4 คือส่วน query
                        reconstructed_url = urlunparse(new_url_parts)

                        if reconstructed_url != target_url:
                            print(f"ตรวจพบ URL Facebook photo, URL เดิม: {target_url}")
                            target_url = reconstructed_url
                            print(f"URL ที่ปรับปรุง (เหลือเฉพาะ fbid): {target_url}")
                except Exception as e:
                    print(f"เกิดข้อผิดพลาดในการประมวลผล URL ของ Facebook photo: {e}. ใช้ URL เดิม: {target_url}")
            # ตอนนี้ target_url คือ URL สุดท้าย (ถ้า Selenium สำเร็จ) หรือ URL เดิม
            if "/photo/" in target_url or "/photos/" in target_url:
                print("ตรวจพบว่าเป็นลิงก์รูปภาพ Facebook (หรือ redirect ไปยังรูปภาพ)")
                output_dir, error = download_image_or_album(target_url, download_folder, single_photo=True)
                if output_dir:
                    description = data.get("caption") or ""
                    result = auto_post_from_folder(access_token, page_id, download_folder, description)
                else:
                    return jsonify({"success": False, "error": f"ไม่สามารถดาวน์โหลดรูปภาพ Facebook ได้: {error}"}), 500
            
            elif "/video/" in target_url or "/reel/" in target_url or "/watch/" in target_url:
                print("ตรวจพบว่าเป็นลิงก์วิดีโอ Facebook (หรือ redirect ไปยังวิดีโอ)")
                video_path, error, youtube_title = download_video_yt_dlp(target_url,
                                                        output_path=os.path.join(download_folder, "download.mp4"))  # รับ title กลับมาด้วย
                if video_path:
                    upscaled_video_path = upscale_video(video_path)
                    if upscaled_video_path:
                        print(f"วิดีโอถูก upscale แล้ว: {upscaled_video_path}")
                        video_path = upscaled_video_path
                    if video_caption_text:
                        captioned_video_path = add_caption_to_video(video_path, video_caption_text)
                        if captioned_video_path:
                            print(f"วิดีโอถูกใส่แคปชันแล้ว: {captioned_video_path}")
                            video_path = captioned_video_path
                        else:
                            print("การใส่แคปชันวิดีโอไม่สำเร็จ จะโพสต์วิดีโอต้นฉบับแทน")
                    description = data.get("caption") or youtube_title or ""  # ใช้ title ถ้าไม่มี caption
                    result = auto_post_from_folder(access_token, page_id, download_folder, description)
                else:
                    return jsonify({"success": False, "error": f"ไม่สามารถดาวน์โหลดวิดีโอ Facebook ได้: {error}"}), 500
            else: # กรณีที่ไม่ใช่ /photo/, /video/, /reel/, /watch/ หรือเป็น URL Facebook ทั่วไป
                print("ไม่สามารถระบุประเภทเนื้อหา Facebook ได้ชัดเจน (photo/video) หรือเป็น URL ทั่วไป, ลองดาวน์โหลดเป็นวิดีโอก่อน")
                video_path, error_video, youtube_title = download_video_yt_dlp(target_url,
                                                        output_path=os.path.join(download_folder, "download.mp4"))
                if video_path:
                    upscaled_video_path = upscale_video(video_path)
                    if upscaled_video_path: video_path = upscaled_video_path
                    if video_caption_text:
                        captioned_video_path = add_caption_to_video(video_path, video_caption_text)
                        if captioned_video_path: video_path = captioned_video_path
                    description = data.get("caption") or youtube_title or ""
                    result = auto_post_from_folder(access_token, page_id, download_folder, description)
                else:
                    print(f"ดาวน์โหลดวิดีโอ Facebook ล้มเหลว ({error_video}), ลองโหลดเป็นรูปภาพ/อัลบั้ม...")
                    # สำหรับ fallback นี้ ให้ลองโหลดเป็นอัลบั้ม (single_photo=False)
                    output_dir, error_img = download_image_or_album(target_url, download_folder, single_photo=False)
                    if output_dir:
                        description = data.get("caption") or ""
                        result = auto_post_from_folder(access_token, page_id, download_folder, description)
                    else:
                        print(f"ดาวน์โหลดรูปภาพ/อัลบั้ม Facebook ล้มเหลว: {error_img}")
                        return jsonify({"success": False, "error": f"ไม่สามารถดาวน์โหลดเนื้อหาจาก Facebook ได้ Video error: {error_video}, Image error: {error_img}"}), 500

        else:
            print("ตรวจพบ URL อื่น...")

            video_path, error, youtube_title = download_video_yt_dlp(target_url, output_path=os.path.join(download_folder, "download.mp4"))  # รับ title กลับมาด้วย
            if video_path:
                # เรียก upscale_video หากเป็นวิดีโอ
                upscaled_video_path = upscale_video(video_path)
                if upscaled_video_path:
                    print(f"วิดีโอถูก upscale แล้ว: {upscaled_video_path}")
                    # แทนที่ video_path ด้วย path ของวิดีโอที่ถูก upscale
                    video_path = upscaled_video_path

                # เรียก add_caption_to_video หลังจาก upscale
                if video_caption_text:
                    captioned_video_path = add_caption_to_video(video_path, video_caption_text)
                    if captioned_video_path:
                        print(f"วิดีโอถูกใส่แคปชันแล้ว: {captioned_video_path}")
                        # แทนที่ video_path ด้วย path ของวิดีโอที่ใส่แคปชัน
                        video_path = captioned_video_path
                    else:
                        print("การใส่แคปชันวิดีโอไม่สำเร็จ จะโพสต์วิดีโอต้นฉบับแทน")
                
                description = data.get("caption") or youtube_title or ""  # ใช้ title ถ้าไม่มี caption
                # เรียก auto_post_from_folder หลังจากที่ add_caption_to_video เสร็จ (ถ้ามี)
                result = auto_post_from_folder(access_token, page_id, download_folder, description)
            else:
                print("ดาวน์โหลดวิดีโอไม่สำเร็จ ลองโหลดเป็นรูปภาพแทน...")
                output_dir, error = download_image_or_album(target_url, download_folder, single_photo=False) # URL อื่นๆ อาจเป็นอัลบั้ม
                if output_dir:
                    result = auto_post_from_folder(access_token, page_id, download_folder, description)
                else:
                    print("ดาวน์โหลดรูปภาพล้มเหลว:", error)
                    return jsonify({"success": False, "error": error}), 500

        print("Result from posting:", result)
        if result and 'id' in result:
            post_id = result['id']
            i = 1
            comment_responses = []
            while True:
                text = data.get(f"comment{i}")
                if not text:
                    print("ไม่มีคอมเมนต์เพิ่มเติม")
                    break
                image_url = data.get(f"comment{i}_image_url")
                if image_url:
                    print(f"พบ image_url สำหรับคอมเมนต์ {i}: {repr(image_url)}")
                    try:
                        res = post_comment_with_image(post_id, text, image_url, access_token)
                        print(f"ผลลัพธ์ post_comment_with_image: {res}")
                    except Exception as e:
                        print(f"โพสต์คอมเมนต์ {i} พร้อมรูปภาพ ล้มเหลว: {e}")
                        res = post_comment(post_id, text, access_token)
                else:
                    print(f"โพสต์คอมเมนต์ {i} ปกติ:", text)
                    res = post_comment(post_id, text, access_token)

                comment_responses.append(res)
                print(f"ผลลัพธ์คอมเมนต์ {i}:", res)
                i += 1
                time.sleep(5)  # Reduced sleep time to 5 seconds

            return jsonify({"success": True, "post_id": post_id, "comments": comment_responses})

        elif result and 'error' in result:
            return jsonify({"success": False, "error": result['error']}), 500
        else:
            return jsonify({"success": False, "error": "ไม่สามารถโพสต์ได้"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    os.makedirs("downloaded", exist_ok=True)
    print("เริ่ม Flask server port 5001")
    app.run(host="0.0.0.0", port=5001, debug=True)