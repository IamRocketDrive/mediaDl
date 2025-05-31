import cv2
import os

def upscale_video(video_path, target_width=540, target_height=960):
    """
    Upscales a video to a target resolution while maintaining aspect ratio.
    If the video is already larger than the target, it returns the original path.

    Args:
        video_path (str): The path to the input video file.
        target_width (int): The desired width for the upscaled video.
        target_height (int): The desired height for the upscaled video.

    Returns:
        str: The path to the upscaled video file, or the original video path
             if no upscaling was needed or if an error occurred.
    """
    print(f"กำลังตรวจสอบและ upscale วิดีโอ: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("ไม่สามารถเปิดวิดีโอได้")
        return video_path

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"ขนาดวิดีโอดั้งเดิม: {width}x{height}")

    # If video is already larger or equal to target, no upscaling needed
    if width >= target_width and height >= target_height:
        print("ขนาดวิดีโอเพียงพอ ไม่ต้อง upscale")
        cap.release()
        return video_path

    # Calculate aspect ratio to maintain proportions
    aspect_ratio = width / height
    target_aspect = target_width / target_height

    if aspect_ratio > target_aspect:
        # Video is wider than target aspect, adjust height based on target width
        new_width = target_width
        new_height = int(new_width / aspect_ratio)
    else:
        # Video is taller than target aspect, adjust width based on target height
        new_height = target_height
        new_width = int(new_height * aspect_ratio)

    # Ensure dimensions are even (required by some video codecs)
    new_width = new_width + (new_width % 2)
    new_height = new_height + (new_height % 2)

    # Define output path
    output_path = os.path.join(os.path.dirname(video_path), "upscaled_video.mp4")
    
    # Define video codec and writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Using 'mp4v' for broader compatibility
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))

    if not out.isOpened():
        print("ไม่สามารถสร้างไฟล์วิดีโอเอาต์พุตได้")
        cap.release()
        return video_path

    print(f"กำลัง upscale เป็นขนาด: {new_width}x{new_height}")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Upscale frame using INTER_CUBIC for better quality
        upscaled_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        out.write(upscaled_frame)

    cap.release()
    out.release()
    print(f"upscale เสร็จสิ้น บันทึกที่: {output_path}")
    return output_path