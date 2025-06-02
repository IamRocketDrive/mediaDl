import os
import googleapiclient.discovery
import googleapiclient.errors
import google.auth
import google.auth.exceptions
import logging

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------- CONFIG ----------
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
# ----------------------------

def get_authenticated_service():
    """
    สร้างและคืนค่า YouTube API service ที่ได้รับการยืนยันตัวตนแล้ว
    จะใช้ Application Default Credentials (ADC) ในการยืนยันตัวตน
    โปรดตรวจสอบว่าคุณได้ตั้งค่า ADC ไว้อย่างถูกต้อง
    (เช่น โดยการรัน 'gcloud auth application-default login'
    หรือตั้งค่า GOOGLE_APPLICATION_CREDENTIALS)
    """
    try:
        credentials, project = google.auth.default(scopes=SCOPES)
        logging.info(f"Application Default Credentials โหลดสำเร็จ (Project: {project or 'N/A'})")

        # Credentials obtained via google.auth.default() are typically auto-refreshing.
        # If they are not valid, API calls will fail.
        return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    except google.auth.exceptions.DefaultCredentialsError:
        logging.error(
            "ไม่สามารถค้นหา Application Default Credentials ได้ "
            "โปรดตรวจสอบว่าคุณได้ตั้งค่า ADC ไว้อย่างถูกต้อง "
            "(เช่น รัน 'gcloud auth application-default login' "
            "หรือตั้งค่า GOOGLE_APPLICATION_CREDENTIALS ไปยังไฟล์ service account key JSON)."
        )
        return None
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดในการสร้าง YouTube service ด้วย ADC: {e}", exc_info=True)
        return None

def upload_youtube_video(video_file_path, video_title, video_description, video_category_id="22", video_privacy_status="public"):
    """
    อัปโหลดวิดีโอไปยัง YouTube

    Args:
        video_file_path (str): Path ของไฟล์วิดีโอที่ต้องการอัปโหลด
        video_title (str): ชื่อวิดีโอ
        video_description (str): คำอธิบายวิดีโอ
        video_category_id (str): ID หมวดหมู่วิดีโอ (เช่น "22" สำหรับ People & Blogs)
        video_privacy_status (str): สถานะความเป็นส่วนตัว ("public", "private", "unlisted")

    Returns:
        dict: Response จาก YouTube API หากอัปโหลดสำเร็จ, หรือ None หากเกิดข้อผิดพลาด
    """
    youtube = get_authenticated_service()
    if not youtube:
        return {"error": "ไม่สามารถเชื่อมต่อกับ YouTube API ได้ (ไม่สามารถรับ ADC credentials หรือ ADC ไม่ถูกต้อง)"}

    if not os.path.exists(video_file_path):
        logging.error(f"ไม่พบไฟล์วิดีโอ: {video_file_path}")
        return {"error": f"ไม่พบไฟล์วิดีโอ: {video_file_path}"}

    request_body = {
        "snippet": {
            "title": video_title,
            "description": video_description,
            "categoryId": video_category_id
        },
        "status": {
            "privacyStatus": video_privacy_status
        }
    }

    try:
        logging.info(f"กำลังอัปโหลดวิดีโอ: {video_file_path} ไปยัง YouTube...")
        media = googleapiclient.http.MediaFileUpload(video_file_path, chunksize=-1, resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        )

        response = request.execute()
        logging.info(f"วิดีโออัปโหลดสำเร็จ: {response.get('id')}")
        return response
    except googleapiclient.errors.HttpError as e:
        logging.error(f"เกิดข้อผิดพลาด HTTP ในการอัปโหลดวิดีโอ: {e}")
        return {"error": f"เกิดข้อผิดพลาด HTTP ในการอัปโหลดวิดีโอ: {e}"}
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิดในการอัปโหลดวิดีโอ: {e}", exc_info=True)
        return {"error": f"เกิดข้อผิดพลาดที่ไม่คาดคิดในการอัปโหลดวิดีโอ: {e}"}

if __name__ == "__main__":
    # ตัวอย่างการใช้งาน:
    # ก่อนรันสคริปต์:
    # 1. เปิดใช้งาน YouTube Data API v3 ใน Google Cloud Console สำหรับโปรเจกต์ของคุณ
    # 2. ตั้งค่า Application Default Credentials (ADC):
    #    - วิธีที่แนะนำสำหรับ local development:
    #      ติดตั้ง Google Cloud CLI (gcloud) และรันคำสั่ง:
    #      gcloud auth application-default login
    #      คำสั่งนี้จะเปิดเบราว์เซอร์เพื่อให้คุณยืนยันตัวตน และบันทึก credentials
    #      ในตำแหน่งที่ ADC สามารถค้นหาได้โดยอัตโนมัติ
    #    - หรือ, สร้าง Service Account Key (ไฟล์ JSON) ใน Google Cloud Console,
    #      ดาวน์โหลดไฟล์ JSON, และตั้งค่า environment variable:
    #      GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
    #      (โปรดระมัดระวังเรื่องความปลอดภัยของไฟล์ service account key)
    # 3. ตรวจสอบว่า SCOPES ที่กำหนด (https://www.googleapis.com/auth/youtube.upload)
    #    ได้รับอนุญาตสำหรับ credentials ที่คุณใช้งาน
    # 4. แก้ไขค่า TEST_VIDEO_FILE ด้านล่างให้เป็น path ของไฟล์วิดีโอของคุณ

    # กำหนดค่าสำหรับวิดีโอทดสอบ
    TEST_VIDEO_FILE = "downloaded/captioned_video.mp4" # หรือชื่อไฟล์วิดีโอที่คุณมี
    TEST_VIDEO_TITLE = "My Test Video Upload"
    TEST_VIDEO_DESC = "This is a test video uploaded via Python script."
    TEST_VIDEO_CATEGORY_ID = "22" # People & Blogs
    TEST_VIDEO_PRIVACY = "private" # public, private, unlisted

    print("--- เริ่มต้นการอัปโหลดวิดีโอทดสอบไปยัง YouTube ---")
    upload_result = upload_youtube_video(
        video_file_path=TEST_VIDEO_FILE,
        video_title=TEST_VIDEO_TITLE,
        video_description=TEST_VIDEO_DESC,
        video_category_id=TEST_VIDEO_CATEGORY_ID,
        video_privacy_status=TEST_VIDEO_PRIVACY
    )

    if upload_result and "id" in upload_result:
        print(f"✅ อัปโหลดวิดีโอสำเร็จ! Video ID: {upload_result['id']}")
        print(f"ลิงก์วิดีโอ: https://www.youtube.com/watch?v={upload_result['id']}")
    else:
        print("❌ การอัปโหลดวิดีโอไม่สำเร็จ")
        if upload_result and "error" in upload_result:
            print(f"ข้อผิดพลาด: {upload_result['error']}")