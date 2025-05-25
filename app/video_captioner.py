import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

def add_caption_to_video(video_path, caption, output_path="captioned_video.mp4", font_size=50, font_color=(255, 255, 255), text_y_position=100):
    """เพิ่มข้อความแคปชันลงในวิดีโอ

    Args:
        video_path (str): เส้นทางไปยังไฟล์วิดีโอต้นฉบับ
        caption (str): ข้อความแคปชันที่จะเพิ่ม
        output_path (str, optional): เส้นทางสำหรับบันทึกวิดีโอที่แก้ไขแล้ว Defaults to "captioned_video.mp4".
        font_size (int, optional): ขนาดตัวอักษร Defaults to 50.
        font_color (tuple, optional): สีตัวอักษร (RGB) Defaults to (255, 255, 255) (สีขาว).
        text_y_position (int, optional): ตำแหน่งแกน Y ของข้อความ Defaults to 100.

    Returns:
        str: เส้นทางไปยังไฟล์วิดีโอที่แก้ไขแล้ว หรือ None หากเกิดข้อผิดพลาด
    """
    print(f"กำลังเพิ่มแคปชัน '{caption}' ลงในวิดีโอ: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ไม่สามารถเปิดวิดีโอได้: {video_path}")
        return None
    print("เปิดวิดีโอสำเร็จ")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if not output_path.lower().endswith('.mp4'):
        output_path = f"{output_path}.mp4"

    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        print(f"ไม่สามารถสร้างไฟล์วิดีโอเอาต์พุตได้: {output_path}")
        cap.release()
        return None

    print(f"ตั้งค่าเอาต์พุตวิดีโอ: {output_path}, FPS: {fps}, ขนาด: {width}x{height}")

    font_path = os.path.join(os.path.dirname(__file__), "NotoSansThai-Bold.ttf")
    try:
        font = ImageFont.truetype(font_path, font_size)
        print("โหลดฟอนต์สำเร็จ:", font_path)
    except IOError:
        print(f"ไม่สามารถโหลดฟอนต์ได้จาก: {font_path} โปรดตรวจสอบว่าไฟล์ฟอนต์อยู่และสามารถเข้าถึงได้")
        cap.release()
        out.release()
        return None

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("สิ้นสุดการอ่านเฟรม")
            break
        frame_count += 1

        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        bbox = draw.textbbox((0, 0), caption, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (img_pil.width - w) // 2
        y = text_y_position

        draw.text((x, y), caption, font=font, fill=font_color)
        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        out.write(frame)

    cap.release()
    out.release()

    print(f"เสร็จสิ้น: เขียน {frame_count} เฟรมลงในไฟล์ {output_path}")
    return os.path.abspath(output_path)

if __name__ == '__main__':
    # ตัวอย่างการใช้งาน (จำลองการรับ path วิดีโอและแคปชัน)
    input_video_path = "download.mp4"
    caption_text = "ตัวอย่างแคปชันที่นี่"
    output_video_path = "modified_video.mp4"

    # สร้างไฟล์วิดีโอทดสอบเปล่าๆ หากไม่มี
    if not os.path.exists(input_video_path):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out_test = cv2.VideoWriter(input_video_path, fourcc, 20.0, (640, 480))
        for i in range(100):
            out_test.write(np.zeros((480, 640, 3), dtype=np.uint8))
        out_test.release()
        print(f"สร้างไฟล์วิดีโอทดสอบ: {input_video_path}")

    result_path = add_caption_to_video(input_video_path, caption_text, output_video_path)
    if result_path:
        print(f"วิดีโอที่ใส่แคปชันแล้วถูกบันทึกที่: {result_path}")
    else:
        print("การใส่แคปชันวิดีโอไม่สำเร็จ")