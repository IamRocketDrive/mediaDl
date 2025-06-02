import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import subprocess  # เพิ่ม module subprocess
import re  # เพิ่ม import re

def get_video_bitrate(video_path, ffmpeg_path="ffmpeg"):
    """ดึงข้อมูล bitrate ของวิดีโอ"""
    try:
        command = [
            ffmpeg_path,
            '-i', video_path,
            '-vcodec', 'copy', '-acodec', 'copy',  # ไม่ต้อง encode ใหม่, แค่เอาข้อมูล
            '-f', 'null', '-'
        ]
        output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode('utf-8')
        match = re.search(r"bitrate: (\d+) kb/s", output)
        if match:
            return int(match.group(1)) * 1000  # Convert kbps to bps
        else:
            print("ไม่พบ bitrate ใน output ของ ffmpeg, ใช้ค่าเริ่มต้น")
            return None
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึง bitrate: {e}, ใช้ค่าเริ่มต้น")
        return None

def add_caption_to_video(video_path, caption, output_path="downloaded/captioned_video.mp4", 
                         font_size=50, font_color=(255, 255, 255), text_y_position=100,
                         output_max_size_mb=None, ffmpeg_path="ffmpeg"):

    print(f"กำลังเพิ่มแคปชัน '{caption}' ลงในวิดีโอ: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ไม่สามารถเปิดวิดีโอได้: {video_path}")
        return None
    print("เปิดวิดีโอสำเร็จ")

    # ดึงข้อมูล bitrate ของวิดีโอต้นฉบับ
    original_bitrate = get_video_bitrate(video_path, ffmpeg_path)
    if original_bitrate:
        print(f"bitrate ของวิดีโอต้นฉบับ: {original_bitrate} bps")
    else:
        print("ไม่สามารถดึง bitrate ของวิดีโอต้นฉบับได้, ใช้ค่าเริ่มต้นในการ encode")

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
    os.remove(video_path)

    print(f"เสร็จสิ้น: เขียน {frame_count} เฟรมลงในไฟล์ {output_path}")


    try:
        compressed_output_path = f"compressed_{os.path.basename(output_path)}"
        compressed_output_path = os.path.join(os.path.dirname(output_path), compressed_output_path)
        
        # ใช้ bitrate เดิมในการบีบอัด (ถ้ามี)
        if original_bitrate:
            command_bitrate = f'{int(original_bitrate / 1000)}k'  # แปลง bps → kbps แล้วเติม k
        else:
            command_bitrate = '5000k'  # Default bitrate

        command = [
            ffmpeg_path,
            '-i', output_path,
            '-b:v', command_bitrate,
            '-maxrate', command_bitrate,
            '-bufsize', '2M',
            '-c:a', 'copy',
            '-y',
            compressed_output_path
        ]

        subprocess.run(command, check=True)
        os.remove(output_path)  # ลบทิ้งก่อนตรวจขนาด

        if is_file_too_large(compressed_output_path, output_max_size_mb):
            os.remove(compressed_output_path)
            print("ไม่สามารถบีบอัดวิดีโอให้ได้ขนาดตามต้องการ")
            return None
        else:
            print(f"บีบอัดวิดีโอสำเร็จ. บันทึกเป็น: {compressed_output_path}")
            return os.path.abspath(compressed_output_path)


    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการบีบอัดวิดีโอ: {e}")
        return None


def is_file_too_large(file_path, max_size_mb=100):
    """ตรวจสอบว่าไฟล์มีขนาดเกินที่กำหนดหรือไม่ (MB)"""
    if max_size_mb is None:
        # ถ้าไม่ได้กำหนดขนาดสูงสุด ให้ถือว่าไฟล์ไม่ใหญ่เกินไปเสมอ
        return False
    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    return file_size_mb > max_size_mb

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

    result_path = add_caption_to_video(input_video_path, caption_text, output_video_path, output_max_size_mb=0.001) # ตั้งค่าขนาดไฟล์สูงสุดเป็น 0.1KB เพื่อทดสอบ
    if result_path:
        print(f"วิดีโอที่ใส่แคปชันแล้วถูกบันทึกที่: {result_path}")
    else:
        print("การใส่แคปชันวิดีโอไม่สำเร็จ")