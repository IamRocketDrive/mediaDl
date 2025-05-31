import os
import requests

def post_reel_to_facebook(page_access_token, page_id, video_path, caption):
    url = f"https://graph.facebook.com/v19.0/{page_id}/videos"
    with open(video_path, 'rb') as video_file:
        files = {'source': video_file}
        data = {
            'access_token': page_access_token,
            'description': caption
        }
        return requests.post(url, files=files, data=data).json()

def post_single_photo_to_facebook(page_access_token, page_id, image_path, caption):
    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    with open(image_path, 'rb') as img_file:
        files = {'source': img_file}
        data = {
            'access_token': page_access_token,
            'caption': caption
        }
        return requests.post(url, files=files, data=data).json()

def post_album_to_facebook(page_access_token, page_id, image_paths, caption):
    photo_ids = []
    for image_path in image_paths:
        with open(image_path, 'rb') as img_file:
            files = {'source': img_file}
            data = {
                'access_token': page_access_token,
                'published': 'false'
            }
            res = requests.post(f'https://graph.facebook.com/v19.0/{page_id}/photos', files=files, data=data)
            res_json = res.json()
            if 'id' in res_json:
                photo_ids.append(res_json['id'])
            else:
                return {'error': res_json}

    attached_media = [{'media_fbid': pid} for pid in photo_ids]
    data = {
        'access_token': page_access_token,
        'message': caption,
        'attached_media': attached_media
    }
    return requests.post(f'https://graph.facebook.com/v19.0/{page_id}/feed', json=data).json()

def auto_post_from_folder(page_access_token, page_id, folder_path, caption=''):
    files = os.listdir(folder_path)
    video_files = [os.path.join(folder_path, f) for f in files if f.lower().endswith('.mp4')]
    image_files = [os.path.join(folder_path, f) for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    if video_files:
        print("พบวิดีโอ => โพสต์เป็น reel")
        return post_reel_to_facebook(page_access_token, page_id, video_files[0], caption)

    elif len(image_files) == 1:
        print("พบรูปเดียว => โพสต์เป็นภาพเดี่ยว")
        return post_single_photo_to_facebook(page_access_token, page_id, image_files[0], caption)

    elif len(image_files) > 1:
        print("พบหลายรูป => โพสต์เป็นอัลบั้ม")
        return post_album_to_facebook(page_access_token, page_id, image_files, caption)

    else:
        print("ไม่พบไฟล์ที่โพสต์ได้")
        return {'error': 'No media found'}

# === วิธีใช้ ===
if __name__ == '__main__':
    page_access_token = 'EAATfRhF7ALkBO8aqvNUtUZANBWDSTomivI5SpS8wQ1jo67SwEKz53vRnfX2t99V4hPB0KmRjkXCuMhUYQU31jKnZB2oKZCbuiNkxr7qLYbJxLZCC8yFy1pkNRbcKrP1uC00ZA8oXe8GZBeUifNTEn6VesBCfZBrNqLQW1sJZB4yQwphUuoSZC6NdML3s0EOadhMoQDKyU95WSKJmS'
    page_id = '325048570702834'
    folder_path = os.path.join(os.getcwd(), 'downloaded')
    result = auto_post_from_folder(page_access_token, page_id, folder_path, caption='โพสต์อัตโนมัติจากโฟลเดอร์')
    print("ผลลัพธ์การโพสต์:", result)
