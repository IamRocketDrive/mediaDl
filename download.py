import json
from flask import Flask, request, jsonify
import instaloader
import re
import os
import subprocess
import shutil
import time
from videoCaptioner import add_caption_to_video
from postToFacebook import auto_post_from_folder
from post_comment import post_comment_with_image,post_comment
from videoUpscale import upscale_video
from getFacebookPhoto import download_facebook_images


app = Flask(__name__)
L = instaloader.Instaloader(dirname_pattern="downloaded")
L.login("AlphonseMcClouds", "#Everfree99")  # ใส่ username และ password จริง

FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"

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

def download_image_or_album(url, output_dir="downloaded"):
    """ดาวน์โหลดรูปภาพหรืออัลบั้มด้วย gallery-dl โดยไม่สร้างโฟลเดอร์ย่อย"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        # กำหนด output template ให้เป็นชื่อไฟล์อย่างเดียว
        # {file.name} คือ placeholder สำหรับชื่อไฟล์เดิม
        os.makedirs(output_dir, exist_ok=True)
        output_template = "{filename}.{extension}"  # รวมนามสกุลไฟล์   
        command = ['gallery-dl', '-q', '-D', output_dir, '-f', output_template, url]

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

    try:
        result = None  # <-- เตรียมตัวแปรไว้ก่อน
        instagram_caption = None
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

            # Check for the specific Facebook share URL pattern
            if "facebook.com/share/p/" in target_url:
                print("URL matches Facebook share pattern. Calling getFacebookPhoto.download_facebook_images")
                download_facebook_images(target_url, download_folder)  # เรียกใช้ฟังก์ชันใหม่
                result = auto_post_from_folder(access_token, page_id, download_folder, description)

            else:
                video_path, error, youtube_title = download_video_yt_dlp(target_url,
                                                        output_path=os.path.join(download_folder, "download.mp4"))  # รับ title กลับมาด้วย
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
                    result = auto_post_from_folder(access_token, page_id, download_folder, description)
                else:
                    print("ดาวน์โหลดวิดีโอ Facebook ล้มเหลว, ลองโหลดเป็นรูปภาพแทน...")
                    output_dir, error = download_image_or_album(target_url, download_folder)
                    if output_dir:
                        result = auto_post_from_folder(access_token, page_id, download_folder, description)
                    else:
                        print("ดาวน์โหลดรูปภาพ Facebook ล้มเหลว:", error)
                        return jsonify({"success": False, "error": error}), 500

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
                output_dir, error = download_image_or_album(target_url, download_folder)
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
                time.sleep(30)  # หน่วงเวลา 30 วินาที ก่อนโพสต์คอมเมนต์ถัดไป

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