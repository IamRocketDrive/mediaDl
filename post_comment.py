# post_comment.py
import requests
import time
from flask import jsonify

def post_comments_with_delay(post_id, comments, access_token, delay=10):
    """โพสต์ชุดคอมเมนต์ลงในโพสต์ Facebook โดยหน่วงเวลาระหว่างโพสต์"""

    print(f"เริ่มโพสต์คอมเมนต์ไปยัง post_id: {post_id} โดยหน่วงเวลา {delay} วินาที")
    comment_responses = []

    try:
        i = 1
        while True:
            text = comments.get(f"comment{i}")
            if not text:
                print("ไม่มีคอมเมนต์เพิ่มเติม")
                break

            image_url = comments.get(f"comment{i}_image_url")
            if image_url:
                print(f"โพสต์คอมเมนต์ {i} พร้อมรูปภาพ: {image_url}")
                res = post_comment_with_image(post_id, text, image_url, access_token)
            else:
                print(f"โพสต์คอมเมนต์ {i} ปกติ: {text}")
                res = post_comment(post_id, text, access_token)

            comment_responses.append(res)
            print(f"ผลลัพธ์คอมเมนต์ {i}: {res}")
            i += 1
            time.sleep(delay)  # หน่วงเวลาก่อนโพสต์คอมเมนต์ถัดไป

        print("โพสต์คอมเมนต์ทั้งหมดเสร็จสิ้น")
        return jsonify({
            "success": True,
            "message": "โพสต์คอมเมนต์สำเร็จ",
            "comment_responses": comment_responses
        })

    except Exception as e:
        error_msg = str(e)
        print(f"เกิดข้อผิดพลาดในการโพสต์คอมเมนต์: {error_msg}")
        return jsonify({
            "success": False,
            "message": "เกิดข้อผิดพลาดในการโพสต์คอมเมนต์",
            "error": error_msg
        }), 500

def post_comment(post_id, comment, access_token):
    """โพสต์คอมเมนต์ข้อความธรรมดา"""

    print(f"โพสต์คอมเมนต์ไปที่ post_id: {post_id}, ข้อความ: {comment}")
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{post_id}/comments",
        data={
            "message": comment,
            "access_token": access_token
        }
    )
    print("ผลลัพธ์การโพสต์คอมเมนต์:", res.json())
    return res.json()

def post_comment_with_image(post_id, comment, image_url, access_token):
    """โพสต์คอมเมนต์พร้อมรูปภาพ"""

    print(f"โพสต์คอมเมนต์พร้อมรูปภาพไปที่ post_id: {post_id}, ข้อความ: {comment}, รูปภาพ: {image_url}")
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{post_id}/comments",
        data={
            "message": comment,
            "attachment_url": image_url,
            "access_token": access_token
        }
    )
    print("ผลลัพธ์การโพสต์คอมเมนต์พร้อมรูปภาพ:", res.json())
    return res.json()