import os
import json
import random
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io

# သင့် Google Drive Folder ID များကို ဒီမှာ ထည့်ပါ
MP3_FOLDER_ID = "1MZyBBGEvDEbMDEBA5JoMh4rj5vJWSsc-"
MP4_FOLDER_ID = "1mU6CFCAU3caRayvn1DjV32V7SlyThlo1"
IMAGE_FOLDER_ID = "1VIwVGGwJiWEbpIoWc3PhHyiPK89G37F1"

# GitHub Secrets မှ သော့များကို ပြန်ခေါ်ခြင်း
creds = Credentials(
    None,
    refresh_token=os.environ["GDRIVE_REFRESH_TOKEN"],
    client_id=os.environ["GDRIVE_CLIENT_ID"],
    client_secret=os.environ["GDRIVE_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token"
)
drive_service = build('drive', 'v3', credentials=creds)

def main():
    # ၁။ MP3 ရှာဖွေခြင်း
    results = drive_service.files().list(
        q=f"'{MP3_FOLDER_ID}' in parents and mimeType='audio/mpeg'",
        fields="files(id, name)"
    ).execute()
    mp3_files = results.get('files', [])
    
    if not mp3_files:
        print("ပြောင်းလဲစရာ MP3 မရှိပါ။")
        return
        
    target_mp3 = mp3_files[0]
    mp3_id = target_mp3['id']
    mp3_name = target_mp3['name'].replace(".mp3", "")
    
    # MP3 ကို GitHub Cloud ပေါ်သို့ ခဏ ဒေါင်းလုပ်ဆွဲခြင်း
    request = drive_service.files().get_media(fileId=mp3_id)
    fh = io.FileIO('input.mp3', 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    # ၂။ ပုံ ၁၅ ပုံကို Random ယူခြင်း
    img_results = drive_service.files().list(
        q=f"'{IMAGE_FOLDER_ID}' in parents and (mimeType='image/jpeg' or mimeType='image/png')",
        fields="files(id, name)"
    ).execute()
    img_files = img_results.get('files', [])
    
    if not img_files:
        print("ပုံများ ရှာမတွေ့ပါ။")
        return
        
    random.shuffle(img_files)
    selected_imgs = img_files[:15]
    
    # ပုံများကို ဒေါင်းလုဒ်ဆွဲပြီး စာရင်းလုပ်ခြင်း
    with open('images.txt', 'w') as f:
        for idx, img in enumerate(selected_imgs):
            img_path = f"img_{idx}.jpg"
            img_req = drive_service.files().get_media(fileId=img['id'])
            with io.FileIO(img_path, 'wb') as img_fh:
                downloader = MediaIoBaseDownload(img_fh, img_req)
                d_done = False
                while not d_done:
                    _, d_done = downloader.next_chunk()
            f.write(f"file '{img_path}'\n")
            f.write("duration 5\n")
        f.write(f"file 'img_0.jpg'\n") # FFmpeg လိုအပ်ချက်အရ

    # ၃။ FFmpeg ဖြင့် ဗီဒီယို အခမဲ့ ပြောင်းလဲခြင်း
    print(f"ဗီဒီယိုအဖြစ် စတင်ပြောင်းလဲနေပါပြီ - {mp3_name}")
    os.system("ffmpeg -y -f concat -safe 0 -i images.txt -i input.mp3 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest output.mp4")

    # ၄။ ရလာတဲ့ MP4 ကို Google Drive သို့ ပြန်တင်ခြင်း
    file_metadata = {'name': f"{mp3_name}.mp4", 'parents': [MP4_FOLDER_ID]}
    media = MediaFileUpload('output.mp4', mimeType='video/mp4')
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print("MP4 ကို Drive ထဲသို့ သိမ်းဆည်းပြီးပါပြီ။")

    # ၅။ ပြီးသွားတဲ့ MP3 ကို အော်တိုဖျက်ခြင်း
    drive_service.files().delete(fileId=mp3_id).execute()
    print("လုပ်ဆောင်ပြီးသား MP3 ကို ဖျက်လိုက်ပါပြီ။")

if __name__ == "__main__":
    main()
