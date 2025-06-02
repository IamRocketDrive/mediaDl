from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

# กำหนดค่าของคุณที่นี่
CLIENT_ID = '562174775855-4u3egrucds921bg6be050tfev1te9ngj.apps.googleusercontent.com'
CLIENT_SECRET = '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'
VIDEO_FILE = 'downloaded/download.mp4'  # เปลี่ยนเป็นไฟล์วิดีโอของคุณ
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_credentials():
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080/"]
            }
        },
        scopes=SCOPES
    )
    creds = flow.run_local_server(port=8080)
    print("REFRESH TOKEN:", creds.refresh_token)
    return creds

def upload_video(creds, video_path, title, description, tags):
    youtube = build('youtube', 'v3', credentials=creds)
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'  # Category: People & Blogs (เปลี่ยนได้ตามต้องการ)
        },
        'status': {
            'privacyStatus': 'private'  # public, private, unlisted
        }
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploading... {int(status.progress() * 100)}%")
    print("Upload Complete!")
    print("Video ID:", response.get('id'))

if __name__ == '__main__':
    creds = get_credentials()
    upload_video(
        creds,
        VIDEO_FILE,
        'Test Video',
        'Uploaded via API',
        ['api', 'test']
    )
