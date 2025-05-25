# postToFacebook.py
import requests
import os
import time
import shutil

def check_reel_status(video_id, access_token):
    print("กำลังตรวจสอบสถานะ reel:", video_id)
    url = f"https://graph.facebook.com/v22.0/{video_id}"
    params = {"access_token": access_token, "fields": "status"}
    for attempt in range(10):
        print(f"พยายามตรวจสอบครั้งที่ {attempt + 1}")
        res = requests.get(url, params=params)
        if res.status_code == 200:
            status = res.json().get("status", {}).get("video_status")
            print(f"สถานะ reel: {status}")
            if status == "ready":
                print("reel พร้อมใช้งาน")
                return True
        time.sleep(30)
        print("รอ 30 วินาทีก่อนตรวจสอบครั้งถัดไป")
    print("หมดเวลาตรวจสอบสถานะ reel")
    return False

def upload_reel_from_file(video_path, description, page_id, access_token):
    print("เริ่มอัปโหลด reel จากไฟล์:", video_path)
    start_url = f"https://graph.facebook.com/v22.0/{page_id}/video_reels"
    print("ส่งคำขอเริ่มอัปโหลด")
    start_res = requests.post(start_url, json={
        "upload_phase": "start",
        "access_token": access_token
    })
    if start_res.status_code != 200:
        print("เริ่มอัปโหลดล้มเหลว:", start_res.json())
        return {"error": "Start upload failed", "details": start_res.json()}

    video_id = start_res.json().get("video_id")
    upload_url = start_res.json().get("upload_url")
    print(f"ได้รับ video_id: {video_id}, upload_url: {upload_url}")

    file_size = os.path.getsize(video_path)
    headers = {
        "Authorization": f"OAuth {access_token}",
        "offset": "0",
        "file_size": str(file_size)
    }
    print(f"อัปโหลดวิดีโอ, ขนาดไฟล์: {file_size} ไบต์")
    with open(video_path, "rb") as f:
        upload_res = requests.post(upload_url, headers=headers, data=f)
    if not upload_res.ok:
        print("อัปโหลดวิดีโอล้มเหลว:", upload_res.json())
        return {"error": "Video upload failed", "details": upload_res.json()}

    finish_url = f"https://graph.facebook.com/v22.0/{page_id}/video_reels"
    print("ส่งคำขอสิ้นสุดการอัปโหลด")
    finish_res = requests.post(finish_url, params={
        "access_token": access_token,
        "video_id": video_id,
        "upload_phase": "finish",
        "video_state": "PUBLISHED",
        "description": description
    })
    result = finish_res.json()
    result["id"] = video_id
    print("ผลลัพธ์การอัปโหลด:", result)
    return result

def create_unpublished_photo_from_file(file_path, page_id, access_token):
    print("สร้างรูปภาพที่ยังไม่เผยแพร่จากไฟล์:", file_path)
    # ตรวจสอบว่า file_path เป็น string
    if not isinstance(file_path, (str, bytes, os.PathLike)):
        print(f"file_path ไม่ถูกต้อง: {file_path} (ต้องเป็น string, bytes หรือ os.PathLike)")
        return None, {"error": f"Invalid file_path type: {type(file_path)}"}
    
    if not os.path.exists(file_path):
        print(f"ไฟล์ไม่พบ: {file_path}")
        return None, {"error": f"File not found: {file_path}"}
    
    if not file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        print(f"ไฟล์ไม่ใช่รูปภาพ: {file_path}")
        return None, {"error": f"Invalid file format: {file_path}"}
    
    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    files = {"source": open(file_path, "rb")}
    data = {
        "published": "false",
        "access_token": access_token
    }
    try:
        res = requests.post(url, files=files, data=data)
        result = res.json()
        print("ผลลัพธ์การสร้างรูปภาพ:", result)
        if "id" in result:
            return result.get("id"), None
        else:
            print(f"เกิดข้อผิดพลาด: {result}")
            return None, result
    except Exception as e:
        print(f"ข้อผิดพลาดในการอัปโหลดไฟล์: {e}")
        return None, {"error": f"Upload error: {str(e)}"}
    finally:
        files["source"].close()

def publish_album(file_paths, caption, page_id, access_token):
    print("เริ่มเผยแพร่อัลบั้มด้วยไฟล์:", file_paths)
    # ตรวจสอบว่า file_paths เป็น list
    if not isinstance(file_paths, list):
        print(f"file_paths ไม่ถูกต้อง: {file_paths} (ต้องเป็น list)")
        return {"success": False, "message": f"Invalid file_paths type: {type(file_paths)}"}
    
    media_ids = []
    errors = []
    
    # สร้างรูปภาพที่ยังไม่เผยแพร่สำหรับแต่ละไฟล์
    for file_path in file_paths:
        media_id, error = create_unpublished_photo_from_file(file_path, page_id, access_token)
        if media_id:
            media_ids.append(media_id)
            print(f"เพิ่ม media_id: {media_id}")
        else:
            print(f"ไม่สามารถสร้าง unpublished photo จาก: {file_path}")
            if error:
                errors.append(error)
    
    if not media_ids:
        print("ไม่พบ media_ids ที่ถูกต้อง")
        return {"success": False, "message": "No valid images found", "errors": errors}

    # เผยแพร่อัลบั้ม
    attached_media = [{"media_fbid": mid} for mid in media_ids]
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{page_id}/feed",
        json={
            "message": caption,
            "attached_media": attached_media,
            "access_token": access_token
        }
    )
    result = res.json()
    print("ผลลัพธ์การเผยแพร่อัลบั้ม:", result)

    if not result.get("id"):
        print("เผยแพร่อัลบั้มล้มเหลว:", result)
        return {"success": False, "message": "Album publish failed", "details": result, "errors": errors}

    post_id = result.get("id")
    return {
        "success": True,
        "message": "Album published successfully",
        "post_id": post_id
    }

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