import os
import requests
import time
import logging

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def post_reel_to_facebook(page_access_token, page_id, video_path, caption):
    """โพสต์วิดีโอเป็น Reel บน Facebook Page."""

    url = f"https://graph.facebook.com/v19.0/{page_id}/videos"
    try:
        with open(video_path, 'rb') as video_file:
            files = {'source': video_file}
            data = {
                'access_token': page_access_token,
                'description': caption
            }
            logging.info(f"กำลังโพสต์ Reel ไปที่ Page ID: {page_id} จากไฟล์: {video_path}")
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()  # ตรวจสอบ HTTP status code

            result = response.json()
            logging.info(f"Facebook API Response: {result}")
            return result

    except requests.exceptions.RequestException as e:
        logging.error(f"เกิดข้อผิดพลาดในการโพสต์ Reel: {e}")
        return {'error': str(e)}
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิดในการโพสต์ Reel: {e}", exc_info=True)
        return {'error': 'เกิดข้อผิดพลาดที่ไม่คาดคิด'}

def post_single_photo_to_facebook(page_access_token, page_id, image_path, caption):
    """โพสต์รูปภาพเดี่ยวบน Facebook Page."""

    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    try:
        with open(image_path, 'rb') as img_file:
            files = {'source': img_file}
            data = {
                'access_token': page_access_token,
                'caption': caption
            }
            logging.info(f"กำลังโพสต์รูปภาพเดี่ยวไปที่ Page ID: {page_id} จากไฟล์: {image_path}")
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()

            result = response.json()
            logging.info(f"Facebook API Response: {result}")
            return result

    except requests.exceptions.RequestException as e:
        logging.error(f"เกิดข้อผิดพลาดในการโพสต์รูปภาพเดี่ยว: {e}")
        return {'error': str(e)}
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิดในการโพสต์รูปภาพเดี่ยว: {e}", exc_info=True)
        return {'error': 'เกิดข้อผิดพลาดที่ไม่คาดคิด'}

def post_album_to_facebook(page_access_token, page_id, image_paths, caption):
    """โพสต์อัลบั้มรูปภาพบน Facebook Page."""

    try:
        photo_ids = []
        for image_path in image_paths:
            with open(image_path, 'rb') as img_file:
                files = {'source': img_file}
                data = {
                    'access_token': page_access_token,
                    'published': 'false'  # สร้างรูปภาพแบบ unpublished ก่อน
                }
                logging.info(f"กำลังอัปโหลดรูปภาพไปยังอัลบั้มจากไฟล์: {image_path}")
                res = requests.post(f'https://graph.facebook.com/v19.0/{page_id}/photos', files=files, data=data)
                res.raise_for_status()

                res_json = res.json()
                if 'id' in res_json:
                    photo_ids.append(res_json['id'])
                    logging.info(f"อัปโหลดรูปภาพสำเร็จ ได้รับ Photo ID: {res_json['id']}")
                else:
                    logging.error(f"เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ: {res_json}")
                    return {'error': res_json}

        attached_media = [{'media_fbid': pid} for pid in photo_ids]
        data = {
            'access_token': page_access_token,
            'message': caption,
            'attached_media': attached_media
        }
        logging.info(f"กำลังสร้างอัลบั้มด้วยรูปภาพ {len(photo_ids)} รูป")
        response = requests.post(f'https://graph.facebook.com/v19.0/{page_id}/feed', json=data)
        response.raise_for_status()

        result = response.json()
        logging.info(f"Facebook API Response: {result}")
        return result

    except requests.exceptions.RequestException as e:
        logging.error(f"เกิดข้อผิดพลาดในการโพสต์อัลบั้ม: {e}")
        return {'error': str(e)}
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิดในการโพสต์อัลบั้ม: {e}", exc_info=True)
        return {'error': 'เกิดข้อผิดพลาดที่ไม่คาดคิด'}

def auto_post_from_folder(page_access_token, page_id, folder_path, caption):
    """โพสต์สื่ออัตโนมัติจากโฟลเดอร์ (Reel, รูปเดี่ยว, อัลบั้ม)."""

    try:
        files = os.listdir(folder_path)
        video_files = [os.path.join(folder_path, f) for f in files if f.lower().endswith('.mp4')]
        image_files = [os.path.join(folder_path, f) for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        if video_files:
            logging.info("พบวิดีโอ => โพสต์เป็น Reel")
            result = post_reel_to_facebook(page_access_token, page_id, video_files[0], caption)
            if 'id' in result:
                reel_id = result['id']
                if check_reel_status(reel_id, page_access_token):
                    return result
                else:
                    return {'error': 'Reel ไม่พร้อมใช้งานหลังจากตรวจสอบหลายครั้ง'}
            else:
                return result

        elif len(image_files) == 1:
            logging.info("พบรูปเดียว => โพสต์เป็นภาพเดี่ยว")
            return post_single_photo_to_facebook(page_access_token, page_id, image_files[0], caption)

        elif len(image_files) > 1:
            logging.info("พบหลายรูป => โพสต์เป็นอัลบั้ม")
            return post_album_to_facebook(page_access_token, page_id, image_files, caption)

        else:
            logging.warning("ไม่พบไฟล์ที่โพสต์ได้ในโฟลเดอร์")
            return {'error': 'No media found'}

    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดในการโพสต์อัตโนมัติจากโฟลเดอร์: {e}", exc_info=True)
        return {'error': 'เกิดข้อผิดพลาดที่ไม่คาดคิด'}

def check_reel_status(video_id, access_token):
    """ตรวจสอบสถานะของ Reel หลังจากโพสต์."""

    logging.info(f"กำลังตรวจสอบสถานะ Reel: {video_id}")
    url = f"https://graph.facebook.com/v22.0/{video_id}"
    params = {"access_token": access_token, "fields": "status"}
    for attempt in range(10):
        logging.info(f"พยายามตรวจสอบสถานะครั้งที่ {attempt + 1}")
        try:
            res = requests.get(url, params=params)
            res.raise_for_status()
            status = res.json().get("status", {}).get("video_status")
            logging.info(f"สถานะ Reel: {status}")
            if status == "ready":
                logging.info("Reel พร้อมใช้งาน")
                return True
        except requests.exceptions.RequestException as e:
            logging.error(f"เกิดข้อผิดพลาดในการตรวจสอบสถานะ: {e}")
        time.sleep(30)
        logging.info("รอ 30 วินาทีก่อนตรวจสอบครั้งถัดไป")
    logging.warning("หมดเวลาตรวจสอบสถานะ Reel")
    return False