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
    mp3_filename = "input_audio.mp3"
    output_tmp = "output_fixed.mp4"
    chosen_img_path = "input_image.jpg"

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
        output_mp4 = f"{os.path.splitext(chosen_mp3['name'])[0]}.mp4"
        download_file(service, chosen_mp3['id'], mp3_filename)

        # ဓာတ်ပုံများထဲမှ ပုံ ၁ ပုံကို ကျပန်း (Random) ရွေးချယ်ပြီး MP3 ကြာချိန်အပြည့် Loop ပတ်ရန်
        # (မှတ်ချက် - ပုံတစ်ပုံချင်းစီကို အသံအဆုံးအထိ ငြိမ်ပြီး ပြသသွားမှာ ဖြစ်လို့ ဖိုင်ဆိုက်လည်း သေးပြီး ပိုမိုမြန်ဆန်ပါတယ်)
        chosen_image = random.choice(image_files)
        download_file(service, chosen_image['id'], chosen_img_path)

        # 2. FFmpeg ဖြင့် MP3 ကြာချိန်အတိုင်း ပုံကို အလိုအလျောက် Loop ပတ်ပြီး ဗီဒီယိုဆောက်ခြင်း
        print("FFmpeg ဖြင့် MP3 ကြာချိန်အလိုက် ဗီဒီယိုကို Loop စတင်ပတ်နေပါပြီ...")
        
        # -loop 1 က ပုံကို ထပ်ခါတလဲလဲ သုံးခိုင်းပြီး၊ -shortest က အသံဆုံးတာနဲ့ ဗီဒီယိုကို ပိတ်ခိုင်းတာ ဖြစ်ပါတယ်
        ffmpeg_cmd = f'ffmpeg -loop 1 -i "{chosen_img_path}" -i "{mp3_filename}" -c:v libx264 -preset ultrafast -tune stillimage -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -y "{output_tmp}"'
        os.system(ffmpeg_cmd)

        # ဗီဒီယိုဖိုင် အမှန်တကယ်ထွက်လာပြီး 0 KB ထက်ကြီးမကြီး စစ်ဆေးခြင်း
        if os.path.exists(output_tmp) and os.path.getsize(output_tmp) > 0:
            os.rename(output_tmp, output_mp4)
            
            # 3. ဗီဒီယိုကို Drive သို့ တင်ခြင်း
            upload_file(service, output_mp4, MP4_FOLDER_ID)
            
            # 4. အသုံးပြုပြီးသား MP3 ဖိုင်ကို Google Drive ပေါ်မှ ချက်ချင်းဖျက်ချခြင်း
            try:
                service.files().delete(fileId=chosen_mp3['id']).execute()
                print(f"Drive ပေါ်မှ အသုံးပြုပြီးသား MP3 ဖိုင် ({chosen_mp3['name']}) ကို အောင်မြင်စွာ ဖျက်ဆီးပြီးပါပြီ။")
            except Exception as delete_error:
                print(f"Drive ပေါ်က MP3 ဖိုင်ဖျက်ရာတွင် အမှားအယွင်းရှိခဲ့သည်: {delete_error}")

        else:
            print("Error: FFmpeg ဗီဒီယို မထုတ်ပေးနိုင်ခဲ့ပါ သို့မဟုတ် ဖိုင်ဆိုက် 0 KB ဖြစ်နေပါသည်!")

    except Exception as e:
        print(f"အောက်ပါ အမှားအယွင်း ဖြစ်ပွားခဲ့သည်: {e}")

    finally:
        # 5. GitHub Actions စက်ရုပ်အတွင်း ကျန်ခဲ့သည့် ယာယီဖိုင်များအားလုံးကို သန့်ရှင်းရေးလုပ်ခြင်း
        print("ယာယီဖိုင်များ သန့်ရှင်းရေး လုပ်ဆောင်နေပါသည်...")
        if os.path.exists(mp3_filename): os.remove(mp3_filename)
        if os.path.exists(chosen_img_path): os.remove(chosen_img_path)
        if os.path.exists(output_tmp): os.remove(output_tmp)
        try:
            if 'output_mp4' in locals() and os.path.exists(output_mp4): 
                os.remove(output_mp4)
        except:
            pass
        print("သန့်ရှင်းရေး ပြီးဆုံးပါပြီ။")

if __name__ == "__main__":
    main()
