from flask import Flask, request, jsonify
import instaloader
import re
import os
import subprocess
import shutil
from video_captioner import add_caption_to_video
from postToFacebook import upload_reel_from_file, check_reel_status, create_unpublished_photo_from_file, publish_album  # นำเข้าฟังก์ชันที่จำเป็น

app = Flask(__name__)
L = instaloader.Instaloader(dirname_pattern="downloaded")

FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"


def download_video_yt_dlp(url, output_path="download/download.mp4"):
    """ดาวน์โหลดวิดีโอด้วย yt-dlp พร้อมรวมเสียง/วิดีโอด้วย FFmpeg"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if os.path.exists(output_path):
            print(f"กำลังลบไฟล์เก่า: {output_path}")
            os.remove(output_path)
            print("ลบไฟล์เก่าแล้วนะ.")

        command = [
            'yt-dlp',
            '-f',
            'bestvideo+bestaudio/best',
            url,
            '-o',
            output_path,
            '--merge-output-format',
            'mp4',
            '--ffmpeg-location',
            FFMPEG_PATH,
            '--remux-video',
            'mp4'
        ]

        print(f"กำลังดาวน์โหลดวิดีโอด้วย yt-dlp จาก: {url}")
        print(f"บันทึกเป็น: {output_path}")
        print(f"ใช้ FFmpeg ที่: {FFMPEG_PATH}")

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print("ดาวน์โหลดและรวมไฟล์เสียง/วิดีโอสำเร็จ!")
            return output_path, None
        else:
            error_message = stderr.decode('utf-8')
            print("เกิดข้อผิดพลาดในการดาวน์โหลดวิดีโอด้วย yt-dlp:")
            print(error_message)
            return None, f"เกิดข้อผิดพลาดในการดาวน์โหลดวิดีโอ: {error_message}"

    except FileNotFoundError as e:
        error_message = f"Error: ไม่พบคำสั่ง yt-dlp หรือ FFmpeg โปรดตรวจสอบการติดตั้ง: {e}"
        print(error_message)
        return None, error_message
    except Exception as e:
        error_message = f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}"
        print(error_message)
        return None, error_message


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
    print("กำลังดาวน์โหลดวิดีโอด้วย shortcode:", shortcode)
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        print("ดึงโพสต์สำเร็จ, เริ่มดาวน์โหลด")
        L.download_post(post, target=shortcode)
        for f in os.listdir("downloaded"):
            if f.endswith(".mp4"):
                print("พบไฟล์วิดีโอ:", f)
                video_path = os.path.join("downloaded", f)
                # ตรวจสอบและ upscale วิดีโอ
                # return upscale_video(video_path)
                return video_path, None
    except Exception as e:
        print("เกิดข้อผิดพลาดในการดาวน์โหลด:", e)
    return None
    
def download_video(shortcode):
    print("กำลังดาวน์โหลดวิดีโอด้วย shortcode:", shortcode)
    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        print("ดึงโพสต์สำเร็จ, เริ่มดาวน์โหลด")
        L.download_post(post, target=shortcode)
        for f in os.listdir("downloaded"):
            if f.endswith(".mp4"):
                print("พบไฟล์วิดีโอ:", f)
                video_path = os.path.join("downloaded", f)
                # ตรวจสอบและ upscale วิดีโอ
                return upscale_video(video_path)
    except Exception as e:
        print("เกิดข้อผิดพลาดในการดาวน์โหลด:", e)
    return None

def upscale_video(video_path, target_width=540, target_height=960):
    print(f"กำลังตรวจสอบและ upscale วิดีโอ: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("ไม่สามารถเปิดวิดีโอได้")
        return video_path

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"ขนาดวิดีโอดั้งเดิม: {width}x{height}")

    if width >= target_width and height >= target_height:
        print("ขนาดวิดีโอเพียงพอ ไม่ต้อง upscale")
        cap.release()
        return video_path

    # คำนวณอัตราส่วนเพื่อรักษา aspect ratio
    aspect_ratio = width / height
    target_aspect = target_width / target_height

    if aspect_ratio > target_aspect:
        # วิดีโอกว้างเกินไป ปรับตามความสูง
        new_height = target_height
        new_width = int(new_height * aspect_ratio)
    else:
        # วิดีโอสูงเกินไป ปรับตามความกว้าง
        new_width = target_width
        new_height = int(new_width / aspect_ratio)

    # ปรับขนาดให้เป็นจำนวนคู่ (จำเป็นสำหรับบาง codec)
    new_width = new_width + (new_width % 2)
    new_height = new_height + (new_height % 2)

    output_path = os.path.join(os.path.dirname(video_path), "upscaled_video.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))

    print(f"กำลัง upscale เป็นขนาด: {new_width}x{new_height}")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Upscale เฟรม
        upscaled_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        out.write(upscaled_frame)

    cap.release()
    out.release()
    print(f"upscale เสร็จสิ้น บันทึกที่: {output_path}")
    return output_path

def extract_instagram_shortcode(url):
    """แยก shortcode จาก URL Instagram"""
    clean_url = url.split('?')[0]
    match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]{5,})', clean_url)
    return match.group(1) if match else None


def is_facebook_image_post(url):
    """ตรวจสอบว่าเป็นโพสต์รูปภาพบน Facebook (อย่างง่าย)"""
    return "/photo" in url or "/posts/" in url


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

@app.route('/download', methods=['POST'])
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
        if is_instagram_url(target_url):
            print("ตรวจพบ URL Instagram...")
            filepath, error = download_instagram_item(target_url, download_folder)
            print(f"ไฟล์ที่ดาวน์โหลดจาก Instagram: {filepath}")
            if filepath and filepath.endswith('.mp4'):
                if video_caption_text:
                    print(f"กำลังเพิ่มแคปชันลงในวิดีโอ Instagram: {video_caption_text}")
                    captioned_video_path = os.path.join(
                        download_folder, "captioned_instagram_video.mp4")
                    final_filepath = add_caption_to_video(
                        filepath, video_caption_text, captioned_video_path)
                    if final_filepath:
                        filepath = final_filepath
                        print(f"วิดีโอที่ใส่แคปชันแล้ว: {filepath}")
                        upload_response = upload_reel_from_file(
                            filepath, description, page_id, access_token)
                        print("ผลลัพธ์การอัปโหลดไป Facebook:", upload_response)
                        if upload_response and upload_response.get("id"):
                            success = True
                            reel_id = upload_response.get("id")
                        else:
                            error = f"อัปโหลดไป Facebook ล้มเหลว: {upload_response.get('error') if upload_response else 'ไม่มีการตอบกลับจากการอัปโหลด'}"
                    else:
                        error = "ไม่สามารถเพิ่มแคปชันลงในวิดีโอ Instagram ได้"
                else:
                    upload_response = upload_reel_from_file(
                        filepath, description, page_id, access_token)
                    print("ผลลัพธ์การอัปโหลดไป Facebook:", upload_response)
                    if upload_response and upload_response.get("id"):
                        success = True
                        reel_id = upload_response.get("id")
                    else:
                        error = f"อัปโหลดไป Facebook ล้มเหลว: {upload_response.get('error') if upload_response else 'ไม่มีการตอบกลับจากการอัปโหลด'}"
            elif filepath:  # กรณีเป็นรูปภาพจาก Instagram
                media_id = create_unpublished_photo_from_file(
                    filepath, page_id, access_token)
                if media_id:
                    media_ids.append(media_id)
                    publish_response = publish_album(
                        media_ids, description, page_id, access_token)
                    if publish_response and publish_response.get("id"):
                        success = True
                    else:
                        error = f"เผยแพร่รูปภาพ Instagram ไป Facebook ล้มเหลว: {publish_response.get('error') if publish_response else 'ไม่มีการตอบกลับจากการเผยแพร่'}"
                else:
                    error = "ไม่สามารถสร้าง unpublished photo บน Facebook ได้"

        elif "facebook.com" in target_url:
            print("ตรวจพบ URL Facebook...")
            if is_facebook_image_post(target_url):
                output_dir, error = download_image_or_album(target_url, download_folder)
                if output_dir:
                    image_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(('.jpg', '.jpeg', '.png', '.gif'))]
                    if not image_files:
                        error = "ไม่พบไฟล์รูปภาพในโฟลเดอร์ที่ดาวน์โหลด"
                        print(error)
                        return jsonify({"success": False, "error": error}), 500
                    
                    # ตรวจสอบว่า image_files เป็น list
                    if not isinstance(image_files, list):
                        error = f"image_files ไม่ใช่ list: {type(image_files)}"
                        print(error)
                        return jsonify({"success": False, "error": error}), 500
                    
                    publish_response = publish_album(image_files, description, page_id, access_token)
                    if publish_response.get("success"):
                        clear_download_folder(download_folder)
                        return jsonify({
                            "success": True,
                            "message": "โพสต์รูปภาพ Facebook สำเร็จ",
                            "post_id": publish_response.get("post_id")
                        })
                    else:
                        error = f"เผยแพร่รูปภาพ Facebook ล้มเหลว: {publish_response.get('message')}"
                        print(error, publish_response.get("details"), publish_response.get("errors"))
                        return jsonify({
                            "success": False,
                            "error": error,
                            "details": publish_response.get("details"),
                            "upload_errors": publish_response.get("errors")
                        }), 500
                else:
                    print("ดาวน์โหลดรูปภาพ Facebook ล้มเหลว:", error)
                    return jsonify({"success": False, "error": error}), 500
            else:
                output_video_filename = os.path.join(
                    download_folder, "facebook_video.mp4")
                filepath, error = download_video_yt_dlp(
                    target_url, output_video_filename)
                if filepath:
                    if video_caption_text:
                        print(
                            f"กำลังเพิ่มแคปชันลงในวิดีโอ Facebook: {video_caption_text}")
                        captioned_video_path = os.path.join(
                            download_folder, "captioned_facebook_video.mp4")
                        final_filepath = add_caption_to_video(
                            filepath, video_caption_text, captioned_video_path)
                        if final_filepath:
                            filepath = final_filepath
                            upload_response = upload_reel_from_file(
                                filepath, description, page_id, access_token)
                            if upload_response and upload_response.get("id"):
                                success = True
                                reel_id = upload_response.get("id")
                            else:
                                error = f"อัปโหลดวิดีโอ Facebook ไป Facebook ล้มเหลว: {upload_response.get('error') if upload_response else 'ไม่มีการตอบกลับจากการอัปโหลด'}"
                        else:
                            error = "ไม่สามารถเพิ่มแคปชันลงในวิดีโอ Facebook ได้"
                    else:
                        upload_response = upload_reel_from_file(
                            filepath, description, page_id, access_token)
                        if upload_response and upload_response.get("id"):
                            success = True
                            reel_id = upload_response.get("id")
                        else:
                            error = f"อัปโหลดวิดีโอ Facebook ไป Facebook ล้มเหลว: {upload_response.get('error') if upload_response else 'ไม่มีการตอบกลับจากการอัปโหลด'}"

        elif target_url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            output_dir, error = download_image_or_album(
                target_url, download_folder)
            if output_dir:
                image_files = [os.path.join(output_dir, f) for f in os.listdir(
                    output_dir) if f.endswith(('.jpg', '.jpeg', '.png', '.gif'))]
                for image_file in image_files:
                    media_id = create_unpublished_photo_from_file(
                        image_file, page_id, access_token)
                    if media_id:
                        media_ids.append(media_id)
                if media_ids:
                    publish_response = publish_album(
                        media_ids, description, page_id, access_token)
                    if publish_response and publish_response.get("id"):
                        success = True
                    else:
                        error = f"เผยแพร่รูปภาพจาก URL โดยตรงไป Facebook ล้มเหลว: {publish_response.get('error') if publish_response else 'ไม่มีการตอบกลับจากการเผยแพร่'}"
                else:
                    error = "ไม่พบรูปภาพที่ดาวน์โหลดจาก URL โดยตรง หรือไม่สามารถสร้าง unpublished photo ได้"

        else:
            output_video_filename = os.path.join(
                download_folder, "downloaded_video.mp4")
            filepath, error = download_video_yt_dlp(
                target_url, output_video_filename)
            if filepath:
                if video_caption_text:
                    print(f"กำลังเพิ่มแคปชันลงในวิดีโอทั่วไป: {video_caption_text}")
                    captioned_video_path = os.path.join(
                        download_folder, "captioned_general_video.mp4")
                    final_filepath = add_caption_to_video(
                        filepath, video_caption_text, captioned_video_path)
                    if final_filepath:
                        filepath = final_filepath
                        upload_response = upload_reel_from_file(
                            filepath, description, page_id, access_token)
                        if upload_response and upload_response.get("id"):
                            success = True
                            reel_id = upload_response.get("id")
                        else:
                            error = f"อัปโหลดวิดีโอจาก URL ทั่วไปไป Facebook ล้มเหลว: {upload_response.get('error') if upload_response else 'ไม่มีการตอบกลับจากการอัปโหลด'}"
                    else:
                        error = "ไม่สามารถเพิ่มแคปชันลงในวิดีโอทั่วไปได้"
                else:
                    upload_response = upload_reel_from_file(
                        filepath, description, page_id, access_token)
                    if upload_response and upload_response.get("id"):
                        success = True
                        reel_id = upload_response.get("id")
                    else:
                        error = f"อัปโหลดวิดีโอจาก URL ทั่วไปไป Facebook ล้มเหลว: {upload_response.get('error') if upload_response else 'ไม่มีการตอบกลับจากการอัปโหลด'}"

        if success:
            if reel_id:
                return jsonify({"success": True, "message": "ดาวน์โหลดและอัปโหลดไป Facebook สำเร็จ", "reel_id": reel_id})
            elif media_ids:
                return jsonify({"success": True, "message": "ดาวน์โหลดและโพสต์รูปภาพไป Facebook สำเร็จ"})
            else:
                return jsonify({"success": True, "message": "ดาวน์โหลดสำเร็จ"})
        else:
            return jsonify({"success": False, "error": error or "เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    os.makedirs("downloaded", exist_ok=True)
    print("เริ่ม Flask server port 5001")
    app.run(host="0.0.0.0", port=5001, debug=True)