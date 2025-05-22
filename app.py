from flask import Flask, request, jsonify
import subprocess
import os
import re # For sanitizing filenames
import shutil # For cleaning up temporary directories and moving files
import requests # For making HTTP requests
import time # For delays, e.g. in check_reel_status
import cv2 # For add_caption_to_video
import numpy as np # For add_caption_to_video
from PIL import Image, ImageDraw, ImageFont # For add_caption_to_video
from deep_translator import GoogleTranslator # For translate_to_thai

app = Flask(__name__)

# === Original Helper Functions (Restored) ===

def clean_downloaded_folder():
    folder = 'downloaded'
    if not os.path.exists(folder):
        print(f"Folder '{folder}' does not exist. Skipping cleanup.")
        return
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                print(f"Deleted file: {file_path}")
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                print(f"Deleted directory: {file_path}")
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

def add_caption_to_video(video_path, caption_text):
    print(f"Adding caption '{caption_text}' to video at {video_path}")
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            return None

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Define the codec and create VideoWriter object
        # MJPG is widely compatible for .avi, use avc1 for .mp4 if available and preferred.
        # For this example, let's output to a new file to avoid read/write issues.
        output_filename = os.path.join(os.path.dirname(video_path), f"captioned_{os.path.basename(video_path)}")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') # For .mp4 output
        out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))

        if not out.isOpened():
            print(f"Error: Could not open video writer for {output_filename}")
            cap.release()
            return None

        # Attempt to load a font. If not found, it might error or use a default.
        # For better font handling, provide a path to a .ttf font file.
        try:
            font = ImageFont.truetype("arial.ttf", 20) # Size 20, common font
        except IOError:
            print("Arial font not found, using default PIL font.")
            font = ImageFont.load_default() # Default PIL font

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert frame to PIL Image
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)

            # Add text
            # Simple text positioning, adjust as needed
            text_position = (10, height - 40) # Bottom-left
            draw.text(text_position, caption_text, font=font, fill=(255, 255, 255, 255)) # White text

            # Convert PIL Image back to OpenCV frame
            frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            out.write(frame)

        cap.release()
        out.release()
        print(f"Successfully added caption. Output at: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"Error adding caption to video: {e}")
        # Ensure resources are released if an error occurs mid-process
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if 'out' in locals() and out.isOpened():
            out.release()
        return None


def check_reel_status(video_id, access_token):
    print(f"Checking reel status for video ID: {video_id}")
    url = f"https://graph.facebook.com/v19.0/{video_id}?fields=status&access_token={access_token}"
    for _ in range(10):  # Check 10 times with a delay
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            status_data = response.json().get("status", {})
            print(f"Current reel status: {status_data}")
            if status_data.get("upload_status") == "complete" and status_data.get("publish_status") == "published":
                return "PUBLISHED"
            elif status_data.get("upload_status") == "error":
                return "ERROR"
        except requests.exceptions.RequestException as e:
            print(f"Error checking reel status: {e}")
            return "ERROR" # Network or API error
        except Exception as e:
            print(f"Unexpected error checking reel status: {e}")
            return "ERROR" # Other errors
        time.sleep(30)  # Wait 30 seconds before checking again
    return "PENDING" # If not published or errored after checks

def upload_reel_from_file(video_path, caption, page_id, access_token):
    print(f"Starting reel upload for {video_path} to page {page_id}")
    # Step 1: Initialize the upload session
    init_url = f"https://graph.facebook.com/v19.0/{page_id}/video_reels"
    init_params = {
        "upload_phase": "start",
        "access_token": access_token
    }
    try:
        init_response = requests.post(init_url, data=init_params)
        init_response.raise_for_status()
        init_data = init_response.json()
        video_id = init_data.get("video_id")
        upload_url = init_data.get("upload_url")

        if not video_id or not upload_url:
            print(f"Failed to initialize reel upload. Response: {init_data}")
            return {"success": False, "message": "Failed to initialize reel upload."}

        print(f"Reel upload initialized. Video ID: {video_id}, Upload URL: {upload_url}")

        # Step 2: Upload the video file
        with open(video_path, 'rb') as video_file:
            headers = {
                "Authorization": f"OAuth {access_token}",
                "Content-Type": "application/octet-stream", # Or video/mp4
                "Content-Length": str(os.path.getsize(video_path))
            }
            upload_response = requests.post(upload_url, headers=headers, data=video_file)
            upload_response.raise_for_status() # Check for HTTP errors
            upload_data = upload_response.json()
            print(f"Video file uploaded. Response: {upload_data}")


        # Step 3: Publish the reel
        publish_url = f"https://graph.facebook.com/v19.0/{page_id}/video_reels"
        publish_params = {
            "access_token": access_token,
            "video_id": video_id,
            "upload_phase": "finish",
            "video_state": "PUBLISHED",
            "description": caption,
            # "title": "My Awesome Reel", # Optional title
        }
        publish_response = requests.post(publish_url, data=publish_params)
        publish_response.raise_for_status()
        publish_data = publish_response.json()
        print(f"Reel publish initiated. Response: {publish_data}")

        if publish_data.get("success") or publish_data.get("id"): # "id" is returned on success for reels
            return {"success": True, "id": video_id, "message": "Reel upload initiated successfully."}
        else:
            return {"success": False, "message": f"Failed to publish reel. Details: {publish_data.get('error', {}).get('message', 'Unknown error')}"}

    except requests.exceptions.RequestException as e:
        print(f"Error during reel upload process: {e}")
        # Attempt to provide more detail if possible from the error response
        error_details = "Network error or no response from Facebook."
        if e.response is not None:
            try:
                error_details = e.response.json().get('error', {}).get('message', e.response.text)
            except ValueError: # If response is not JSON
                error_details = e.response.text
        return {"success": False, "message": f"Error during reel upload: {error_details}"}
    except Exception as e:
        print(f"An unexpected error occurred during reel upload: {e}")
        return {"success": False, "message": f"An unexpected error occurred: {str(e)}"}

def publish_album(media_ids, caption, page_id, access_token):
    print(f"Publishing album with media IDs {media_ids} and caption '{caption}' to page {page_id}")
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    attached_media = [{'media_fbid': media_id} for media_id in media_ids]
    params = {
        'message': caption,
        'attached_media': str(attached_media).replace("'", "\""), # API expects JSON string for attached_media
        'access_token': access_token
    }
    try:
        response = requests.post(url, data=params)
        response.raise_for_status() # Raise an exception for HTTP errors
        response_data = response.json()
        print(f"Album published successfully. Response: {response_data}")
        return {"success": True, "id": response_data.get("id"), "message": "Album published successfully."}
    except requests.exceptions.RequestException as e:
        print(f"Error publishing album: {e}")
        error_details = "Network error or no response from Facebook."
        if e.response is not None:
            try:
                error_details = e.response.json().get('error',{}).get('message', e.response.text)
            except ValueError:
                error_details = e.response.text
        return {"success": False, "message": f"Error publishing album: {error_details}"}
    except Exception as e:
        print(f"An unexpected error occurred publishing album: {e}")
        return {"success": False, "message": f"An unexpected error: {str(e)}"}

def post_comment(post_id, message, access_token):
    print(f"Posting comment '{message}' to post ID {post_id}")
    url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
    params = {
        'message': message,
        'access_token': access_token
    }
    try:
        response = requests.post(url, data=params)
        response.raise_for_status()
        print(f"Comment posted successfully. Response: {response.json()}")
        return {"success": True, "message": "Comment posted."}
    except requests.exceptions.RequestException as e:
        print(f"Error posting comment: {e}")
        return {"success": False, "message": f"Failed to post comment: {e}"}

def post_comment_with_image(post_id, message, image_url, access_token):
    print(f"Posting comment with image '{image_url}' and message '{message}' to post ID {post_id}")
    url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
    params = {
        'message': message,
        'attachment_url': image_url,
        'access_token': access_token
    }
    try:
        response = requests.post(url, data=params)
        response.raise_for_status()
        print(f"Comment with image posted successfully. Response: {response.json()}")
        return {"success": True, "message": "Comment with image posted."}
    except requests.exceptions.RequestException as e:
        print(f"Error posting comment with image: {e}")
        return {"success": False, "message": f"Failed to post comment with image: {e}"}

def translate_to_thai(text):
    print(f"Translating to Thai: '{text}'")
    if not text or not text.strip():
        return ""
    try:
        translated = GoogleTranslator(source='auto', target='th').translate(text)
        return translated if translated else ""
    except Exception as e:
        print(f"Error during translation: {e}")
        return text # Return original text if translation fails

# === Existing/Modified Helper Functions ===

def extract_shortcode(url):
    print(f"Extracting shortcode from URL: {url}")
    match = re.search(r"(?:instagram\.com/(?:p|reel|tv)/|instagr\.am/(?:p|reel|tv)/)([\w-]+)", url)
    if match:
        return match.group(1)
    print(f"Could not extract shortcode from {url}")
    return None

def sanitize_filename(filename):
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.replace("..", "")
    return filename

def upscale_video(video_path): # This is kept as per previous logic, called by download_instagram_video
    print(f"Placeholder: Upscaling video at {video_path}")
    return video_path 

def download_other_video(url): # Removed upscale_video call from here
    print(f"Downloading non-Instagram video from: {url} using yt-dlp (general)")
    download_folder = "downloaded"
    os.makedirs(download_folder, exist_ok=True)
    try:
        output_template = os.path.join(download_folder, "%(title)s.%(ext)s")
        result = subprocess.run(
            ['yt-dlp', '-o', output_template, '--merge-output-format', 'mp4', url],
            check=True, capture_output=True, text=True
        )
        print(f"yt-dlp stdout for {url}: {result.stdout}")
        output_lines = result.stdout.splitlines()
        downloaded_file_path = None
        for line in output_lines:
            if "Destination:" in line:
                downloaded_file_path = line.split("Destination:", 1)[1].strip()
                break
            elif "Merging formats into" in line:
                match = re.search(r"Merging formats into \"([^\"]+)\"", line)
                if match:
                    downloaded_file_path = match.group(1)
                    break
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            print(f"Found downloaded video (general): {downloaded_file_path}")
            return downloaded_file_path # No upscale_video here
        else: # Fallback
             for filename in os.listdir(download_folder):
                if filename.endswith(".mp4"):
                    potential_path = os.path.join(download_folder, filename)
                    print(f"Found downloaded video (general, fallback scan): {potential_path}")
                    return potential_path # No upscale_video here
        print(f"Could not reliably determine downloaded file for {url} in {download_folder}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error downloading video from {url} with yt-dlp: {e.stderr}")
        return None
    except FileNotFoundError:
        print("yt-dlp not found. Please ensure it is installed and in PATH.")
        return None

def download_instagram_video(shortcode): # Calls upscale_video internally
    print(f"Downloading Instagram video with yt-dlp for shortcode: {shortcode}")
    url = f"https://www.instagram.com/p/{shortcode}/"
    output_dir = "downloaded"
    os.makedirs(output_dir, exist_ok=True)
    base_filename = sanitize_filename(shortcode)
    output_template = os.path.join(output_dir, f"{base_filename}.%(ext)s")
    try:
        result = subprocess.run(
            ["yt-dlp", "-o", output_template, "--merge-output-format", "mp4", "--no-playlist", url],
            check=True, capture_output=True, text=True
        )
        print(f"yt-dlp stdout: {result.stdout}")
        downloaded_file = None
        for ext in ['.mp4', '.mkv', '.webm']:
            potential_file = os.path.join(output_dir, base_filename + ext)
            if os.path.exists(potential_file):
                downloaded_file = potential_file
                break
        if downloaded_file:
            print(f"Found downloaded video: {downloaded_file}")
            return upscale_video(downloaded_file) # Upscaling for IG video
        else:
            for filename_in_dir in os.listdir(output_dir):
                if filename_in_dir.startswith(base_filename) and filename_in_dir.endswith(('.mp4', '.webm', '.mkv')):
                    downloaded_file = os.path.join(output_dir, filename_in_dir)
                    print(f"Found downloaded video (fallback search): {downloaded_file}")
                    return upscale_video(downloaded_file) # Upscaling for IG video
            print(f"No video file found matching pattern for shortcode {shortcode} in {output_dir}")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error downloading Instagram video with yt-dlp for {shortcode}: {e.stderr}")
        return None
    except FileNotFoundError:
        print("yt-dlp not found. Please ensure it is installed and in PATH.")
        return None

def download_instagram_image(shortcode):
    print(f"Downloading Instagram image(s) with gallery-dl for shortcode: {shortcode}")
    url = f"https://www.instagram.com/p/{shortcode}/"
    output_dir = "downloaded"
    os.makedirs(output_dir, exist_ok=True)
    sane_shortcode = sanitize_filename(shortcode)
    temp_download_subdir = os.path.join(output_dir, f"temp_gallery_{sane_shortcode}")
    os.makedirs(temp_download_subdir, exist_ok=True)
    downloaded_image_paths = []
    try:
        process = subprocess.run(
            ["gallery-dl", "-D", temp_download_subdir, url],
            check=True, capture_output=True, text=True
        )
        print(f"gallery-dl output for {shortcode}: {process.stdout}")
        for root, _, files in os.walk(temp_download_subdir):
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    temp_file_path = os.path.join(root, filename)
                    unique_filename = f"{sane_shortcode}_{sanitize_filename(filename)}"
                    final_image_path = os.path.join(output_dir, unique_filename)
                    shutil.move(temp_file_path, final_image_path)
                    downloaded_image_paths.append(final_image_path)
        if not downloaded_image_paths:
            print(f"No images found or moved for {shortcode} from {temp_download_subdir}")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading Instagram image with gallery-dl for {shortcode}: {e.stderr}")
    except FileNotFoundError:
        print("gallery-dl not found. Please ensure it is installed and in PATH.")
    except Exception as e:
        print(f"An unexpected error in download_instagram_image for {shortcode}: {e}")
    finally:
        if os.path.exists(temp_download_subdir):
            shutil.rmtree(temp_download_subdir)
            print(f"Cleaned up temporary directory: {temp_download_subdir}")
    if downloaded_image_paths:
         print(f"Successfully downloaded and moved images for {shortcode}: {downloaded_image_paths}")
    return downloaded_image_paths

def create_unpublished_photo(media_path, page_id, access_token): # Modified version
    print(f"Creating unpublished photo from local path: {media_path} for page_id: {page_id}")
    try:
        with open(media_path, "rb") as f:
            files = {"source": (os.path.basename(media_path), f)}
            data_payload = {"published": "false", "access_token": access_token}
            res = requests.post(
                f"https://graph.facebook.com/v19.0/{page_id}/photos",
                files=files, data=data_payload
            )
        response_json = res.json()
        print(f"Response from create_unpublished_photo ({res.status_code}): {response_json}")
        if res.status_code == 200 and response_json.get("id"):
            return response_json.get("id")
        else:
            error_details = response_json.get('error', {})
            print(f"Error creating unpublished photo: {error_details.get('message', 'Unknown error')}. Details: {error_details}")
            return None
    except FileNotFoundError:
        print(f"Media file not found at path: {media_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error or Facebook API request issue in create_unpublished_photo: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in create_unpublished_photo: {e}")
        return None

def download_video(url): # General dispatcher
    print(f"Attempting to download video from URL: {url}")
    if "instagram.com" in url:
        shortcode = extract_shortcode(url)
        if shortcode:
            return download_instagram_video(shortcode)
        else:
            print("Invalid Instagram URL or no shortcode found for video download.")
            return None
    elif any(domain in url for domain in ["youtube.com", "youtu.be", "facebook.com", "tiktok.com"]):
        return download_other_video(url)
    else:
        print(f"URL not supported for video download: {url}")
        return None

# === Main Flask Route ===

@app.route('/fetch', methods=['POST'])
def fetch_media_and_post():
    data = request.get_json()
    url = data.get('url')
    page_id = data.get('page_id')
    access_token = data.get('access_token')
    caption = data.get("caption") or "" # Restored caption variable
    video_caption_text = data.get("videoCaption") # Specific for adding text to video

    if not url or not page_id or not access_token:
        return jsonify({"error": "Missing URL, page_id, or access_token"}), 400

    try:
        translated_main_caption = translate_to_thai(caption.strip())

        if "instagram.com" in url:
            shortcode = extract_shortcode(url)
            if not shortcode:
                return jsonify({"success": False, "message": "Could not extract Instagram shortcode"}), 400

            video_path = download_instagram_video(shortcode) # This already calls upscale_video
            if video_path:
                print(f"Instagram video downloaded: {video_path}")
                
                if video_caption_text and video_caption_text.strip():
                    video_path_captioned = add_caption_to_video(video_path, video_caption_text.strip())
                    if not video_path_captioned:
                        clean_downloaded_folder()
                        return jsonify({"success": False, "message": "Failed to add caption to video."}), 500
                    video_path = video_path_captioned # Use the captioned video path
                
                # Use original upload_reel_from_file
                upload_response = upload_reel_from_file(video_path, translated_main_caption, page_id, access_token)
                clean_downloaded_folder()

                if upload_response.get("success") and upload_response.get("id"):
                    video_fb_id = upload_response["id"]
                    status = check_reel_status(video_fb_id, access_token)
                    if status == "PUBLISHED":
                        # Commenting loop
                        for i in range(1, 6): # Max 5 comments
                            comment_text = data.get(f"comment{i}")
                            comment_image_url = data.get(f"comment{i}_image_url")
                            if comment_text:
                                if comment_image_url:
                                    post_comment_with_image(video_fb_id, comment_text, comment_image_url, access_token)
                                else:
                                    post_comment(video_fb_id, comment_text, access_token)
                        return jsonify({"success": True, "message": f"Reel published successfully with ID: {video_fb_id}. Status: {status}", "post_id": video_fb_id})
                    else:
                        return jsonify({"success": False, "message": f"Reel upload initiated but status is {status}. Video ID: {video_fb_id}", "post_id": video_fb_id})
                else:
                    return jsonify({"success": False, "message": upload_response.get("message", "Failed to upload reel.")})

            else: # Instagram image path
                print(f"Failed to download Instagram post {shortcode} as video, attempting as image(s).")
                image_paths = download_instagram_image(shortcode)
                if image_paths:
                    print(f"Instagram image(s) downloaded: {image_paths}")
                    media_ids = []
                    for img_path in image_paths:
                        photo_id = create_unpublished_photo(img_path, page_id, access_token)
                        if photo_id:
                            media_ids.append(photo_id)
                        else:
                            print(f"Failed to create unpublished photo for {img_path}")
                    
                    clean_downloaded_folder() # Clean after uploads attempt

                    if not media_ids:
                        return jsonify({"success": False, "message": "Downloaded images but failed to upload any to Facebook."}), 500
                    
                    # Use original publish_album
                    album_response = publish_album(media_ids, translated_main_caption, page_id, access_token)
                    if album_response.get("success") and album_response.get("id"):
                        album_fb_id = album_response["id"]
                        # Commenting loop
                        for i in range(1, 6):
                            comment_text = data.get(f"comment{i}")
                            comment_image_url = data.get(f"comment{i}_image_url")
                            if comment_text:
                                if comment_image_url:
                                    post_comment_with_image(album_fb_id, comment_text, comment_image_url, access_token)
                                else:
                                    post_comment(album_fb_id, comment_text, access_token)
                        return jsonify({"success": True, "message": f"Album published successfully with ID: {album_fb_id}", "post_id": album_fb_id})
                    else:
                        return jsonify({"success": False, "message": album_response.get("message", "Failed to publish album.")})
                else:
                    clean_downloaded_folder()
                    return jsonify({"success": False, "message": f"Failed to download Instagram content for {shortcode} as video or image."}), 500
        
        # Non-Instagram Video (YouTube, Facebook, TikTok, etc.)
        elif any(domain in url for domain in ["youtube.com", "youtu.be", "facebook.com", "tiktok.com"]):
            video_path = download_video(url) # Calls download_other_video which no longer upscales
            if video_path:
                print(f"Non-Instagram video downloaded: {video_path}")

                if video_caption_text and video_caption_text.strip():
                    video_path_captioned = add_caption_to_video(video_path, video_caption_text.strip())
                    if not video_path_captioned:
                        clean_downloaded_folder()
                        return jsonify({"success": False, "message": "Failed to add caption to video."}), 500
                    video_path = video_path_captioned

                upload_response = upload_reel_from_file(video_path, translated_main_caption, page_id, access_token)
                clean_downloaded_folder()

                if upload_response.get("success") and upload_response.get("id"):
                    video_fb_id = upload_response["id"]
                    status = check_reel_status(video_fb_id, access_token)
                    if status == "PUBLISHED":
                         for i in range(1, 6):
                            comment_text = data.get(f"comment{i}")
                            comment_image_url = data.get(f"comment{i}_image_url")
                            if comment_text:
                                if comment_image_url:
                                    post_comment_with_image(video_fb_id, comment_text, comment_image_url, access_token)
                                else:
                                    post_comment(video_fb_id, comment_text, access_token)
                        return jsonify({"success": True, "message": f"Reel published successfully with ID: {video_fb_id}. Status: {status}", "post_id": video_fb_id})
                    else:
                        return jsonify({"success": False, "message": f"Reel upload initiated but status is {status}. Video ID: {video_fb_id}", "post_id": video_fb_id})
                else:
                    return jsonify({"success": False, "message": upload_response.get("message", "Failed to upload reel.")})
            else:
                clean_downloaded_folder()
                return jsonify({"success": False, "message": "Failed to download video using yt-dlp."}), 500
        else:
            # Removed generic gallery-dl block as per instructions
            return jsonify({"success": False, "message": f"URL type not supported for automated posting: {url}"}), 400

    except Exception as e:
        print(f"An unexpected error occurred in /fetch: {str(e)}")
        import traceback
        traceback.print_exc()
        clean_downloaded_folder() # Clean up in case of unexpected error
        return jsonify({"success": False, "message": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    print("Creating 'downloaded' folder if it doesn't exist.")
    os.makedirs("downloaded", exist_ok=True)
    print("Starting Flask server on port 5001.")
    app.run(host="0.0.0.0", port=5001)
