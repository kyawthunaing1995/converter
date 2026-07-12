import os
import random
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ==========================================
# ⚠️ သင့် Google Drive Folder ID များကို ဤနေရာတွင် ထည့်ပါ
# ==========================================
MP3_FOLDER_ID = "1MZyBBGEvDEbMDEBA5JoMh4rj5vJWSsc-"
MP4_FOLDER_ID = "1mU6CFCAU3caRayvn1DjV32V7SlyThlo1"
IMAGE_FOLDER_ID = "1VIwVGGwJiWEbpIoWc3PhHyiPK89G37F1"

def get_gdrive_service():
    client_id = os.environ.get("GDRIVE_CLIENT_ID")
    client_secret = os.environ.get("GDRIVE_CLIENT_SECRET")
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Error: GitHub Secrets ထဲမှာ သော့ချက်များ လိုအပ်နေပါသေးတယ်!")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )
    return build('drive', 'v3', credentials=creds)

def list_files_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query, 
        fields="files(id, name, mimeType)",
        pageSize=100
    ).execute()
    return results.get('files', [])

def download_file(service, file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    with open(file_name, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
    print(f"Downloaded: {file_name}")

def upload_file(service, file_name, folder_id):
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_name, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Uploaded: {file_name} to Drive (ID: {file.get('id')})")

def main():
    try:
        service = get_gdrive_service()
        
        # 1. Folder များကို စစ်ဆေးခြင်း
        mp3_files = list_files_in_folder(service, MP3_FOLDER_ID)
        image_files = list_files_in_folder(service, IMAGE_FOLDER_ID)
        
        if not mp3_files:
            print("MP3 folder ထဲမှာ ဘာဖိုင်မှ မရှိပါ!")
            return
        if not image_files:
            print("Image folder ထဲမှာ ဘာပုံမှ မရှိပါ!")
            return

        # MP3 ဖိုင်တစ်ဖိုင် ရွေးချယ်ခြင်း
        chosen_mp3 = random.choice(mp3_files)
        mp3_filename = "input.mp3"
        download_file(service, chosen_mp3['id'], mp3_filename)

        # ပုံ ၁၅ ပုံ Random ရွေးချယ်ခြင်း
        sample_size = min(15, len(image_files))
        chosen_images = random.sample(image_files, sample_size)
        
        image_paths = []
        for i, img in enumerate(chosen_images):
            img_filename = f"img_{i}.jpg"
            download_file(service, img['id'], img_filename)
            image_paths.append(img_filename)

        # 2. FFmpeg ဖြင့် ဗီဒီယိုပြောင်းခြင်း
        output_mp4 = f"{os.path.splitext(chosen_mp3['name'])[0]}.mp4"
        
        with open("images.txt", "w") as f:
            for img_path in image_paths:
                f.write(f"file '{img_path}'\n")
                f.write("duration 5\n")
            f.write(f"file '{image_paths[-1]}'\n")

        ffmpeg_cmd = f"ffmpeg -f concat -safe 0 -i images.txt -i {mp3_filename} -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest -y \"{output_mp4}\""
        os.system(ffmpeg_cmd)

        # 3. ဗီဒီယိုကို Drive သို့ တင်ခြင်း နှင့် MP3 ဖိုင်ဟောင်းကို ဖျက်ခြင်း
        if os.path.exists(output_mp4):
            upload_file(service, output_mp4, MP4_FOLDER_ID)
            
            # --- 🌟 ဤနေရာတွင် Google Drive ပေါ်မှ MP3 ဖိုင်ကို လှမ်းဖျက်ပါသည် ---
            try:
                service.files().delete(fileId=chosen_mp3['id']).execute()
                print(f"Drive ပေါ်မှ အသုံးပြုပြီးသား MP3 ဖိုင် ({chosen_mp3['name']}) ကို အောင်မြင်စွာ ဖျက်ဆီးပြီးပါပြီ။")
            except Exception as delete_error:
                print(f"Drive ပေါ်က MP3 ဖိုင်ဖျက်ရာတွင် အမှားအယွင်းရှိခဲ့သည်: {delete_error}")
            # ----------------------------------------------------

            # GitHub စက်ရုပ်ထဲမှ ယာယီဖိုင်များကို ရှင်းလင်းခြင်း
            os.remove(mp3_filename)
            os.remove("images.txt")
            os.remove(output_mp4)
            for img_path in image_paths:
                os.remove(img_path)
            print("သန့်ရှင်းရေး လုပ်ဆောင်ပြီးပါပြီ။ Process အားလုံး အောင်မြင်ပါသည်။")
        else:
            print("Error: FFmpeg ဗီဒီယို မထုတ်ပေးနိုင်ခဲ့ပါ!")

    except Exception as e:
        print(f"အောက်ပါ အမှားအယွင်း ဖြစ်ပွားခဲ့သည်: {e}")

if __name__ == "__main__":
    main()
