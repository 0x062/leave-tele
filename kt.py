import asyncio
import os
import time
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession # Umum diimpor, meski sesi file yg utama
from dotenv import load_dotenv

# --- KONFIGURASI EKSEKUSI OTOMATIS ---
# Jika True, skrip akan otomatis memproses SEMUA item (grup/channel/bot)
# yang tidak di-whitelist tanpa meminta konfirmasi pilihan item.
# Login awal via terminal mungkin masih diperlukan jika sesi tidak ada/valid.
AUTOMATIC_PROCESS_ALL = True

# Jeda normal antar operasi utama (seperti leave atau block/delete per item)
# Tingkatkan jika Anda sering kena FloodWaitError atau untuk operasi batch besar.
NORMAL_ACTION_DELAY = 5  # detik (dinaikkan untuk mode otomatis di VPS)
# Buffer tambahan untuk FloodWaitError (ditambahkan ke waktu tunggu dari Telegram)
FLOOD_WAIT_BUFFER = 15 # detik (dinaikkan untuk mode otomatis di VPS)
# -----------------------------------------

# Muat variabel dari .env
load_dotenv()

API_ID_STR = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

if not API_ID_STR or not API_HASH:
    print("Kesalahan: TELEGRAM_API_ID atau TELEGRAM_API_HASH tidak ditemukan di file .env.")
    exit(1)

try:
    API_ID = int(API_ID_STR)
except ValueError:
    print(f"Kesalahan: TELEGRAM_API_ID ('{API_ID_STR}') harus berupa angka.")
    exit(1)

SESSION_FILE_NAME = 'my_telegram_session.session'
WHITELIST_FILE_PATH = 'whitelist.txt'

def load_whitelist_usernames():
    usernames = []
    try:
        if os.path.exists(WHITELIST_FILE_PATH):
            print(f"Memuat whitelist usernames dari {WHITELIST_FILE_PATH}...")
            with open(WHITELIST_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    username = line.strip().lower()
                    if username:
                        usernames.append(username)
            if usernames:
                print(f"{len(usernames)} username berhasil dimuat dari whitelist.")
            else:
                print(f"File whitelist '{WHITELIST_FILE_PATH}' ditemukan, tetapi kosong.")
        else:
            print(f"Peringatan: File whitelist '{WHITELIST_FILE_PATH}' tidak ditemukan. Tidak ada username yang di-whitelist.")
    except Exception as e:
        print(f"Peringatan: Gagal memuat whitelist dari '{WHITELIST_FILE_PATH}': {e}")
    return usernames

async def main():
    print(f"Memulai skrip Telegram (v10 - Mode Otomatis)...")
    if AUTOMATIC_PROCESS_ALL:
        print("MODE OTOMATIS AKTIF: Akan memproses semua item non-whitelist.")
    
    lower_case_whitelist_usernames = load_whitelist_usernames()

    client = TelegramClient(SESSION_FILE_NAME, API_ID, API_HASH, 
                            retry_delay=10, # Waktu tunggu antar percobaan koneksi jika gagal
                            connection_retries=5) # Jumlah percobaan koneksi

    print("Mencoba menghubungkan ke Telegram...")
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Sesi tidak terotorisasi. Memulai proses login (membutuhkan input manual)...")
            phone_number = input('Masukkan nomor telepon Anda (format +62xxxx): ')
            await client.send_code_request(phone_number)
            try:
                await client.sign_in(phone_number, input('Masukkan kode yang Anda terima: '))
            except errors.SessionPasswordNeededError:
                await client.sign_in(password=input('Masukkan kata sandi Two-Factor Authentication (2FA) Anda: '))
            print("Login berhasil, file sesi telah dibuat/diperbarui.")
        
        me = await client.get_me()
        print(f"\nBerhasil terhubung sebagai: {me.first_name} (@{me.username if me.username else 'Tanpa Username'})")
        print("---\n")

        if not AUTOMATIC_PROCESS_ALL:
            lanjut = input('Lanjutkan untuk mendapatkan daftar grup/channel dan memilih mana yang akan ditinggalkan? (y/n): ').lower()
            if lanjut != 'y':
                print('Proses dibatalkan oleh pengguna.')
                return
        else:
            print("Melanjutkan proses secara otomatis...")


        print('\nMengumpulkan daftar dialog... Mohon tunggu...')
        all_dialogs_api = []
        async for dialog in client.iter_dialogs():
            all_dialogs_api.append(dialog)
        
        groups_channels_to_process = []
        bots_to_process = []
        whitelisted_dialogs_log_ids = set()

        print("Memfilter dialog dan menerapkan whitelist...")
        for dialog in all_dialogs_api:
            entity = dialog.entity
            title = dialog.title
            username = None
            is_bot_flag = False

            if hasattr(entity, 'username') and entity.username:
                username = entity.username.lower()
            
            if isinstance(entity, types.User) and entity.bot:
                is_bot_flag = True

            is_whitelisted = False
            if username and username in lower_case_whitelist_usernames:
                is_whitelisted = True
            
            if is_whitelisted:
                if dialog.id not in whitelisted_dialogs_log_ids:
                    display_title = title if title else (f"@{username}" if username else "N/A")
                    print(f"   -> \"{display_title}\" ada di WHITELIST, akan dilewati.")
                    whitelisted_dialogs_log_ids.add(dialog.id)
                continue 

            if is_bot_flag:
                bots_to_process.append(dialog.entity) # Simpan entity langsung
            elif dialog.is_group or dialog.is_channel:
                groups_channels_to_process.append(dialog.entity) # Simpan entity langsung


        if whitelisted_dialogs_log_ids:
            print(f"\nTotal {len(whitelisted_dialogs_log_ids)} item terdeteksi dalam whitelist dan tidak akan diproses.")

        # --- Fase 1: Keluar dari Grup/Channel ---
        print("\n--- FASE 1: KELUAR DARI GRUP/CHANNEL ---")
        if not groups_channels_to_process:
            print("Tidak ada grup/channel yang perlu diproses (setelah filter whitelist).")
        else:
            print(f"Mode Otomatis: Akan mencoba keluar dari {len(groups_channels_to_process)} grup/channel.")
            for entity_obj in groups_channels_to_process:
                title_to_leave = entity_obj.title if hasattr(entity_obj, 'title') else (f"@{entity_obj.username}" if hasattr(entity_obj, 'username') else f"ID:{entity_obj.id}")
                print(f"Mencoba meninggalkan: \"{title_to_leave}\"...")
                try:
                    await client.delete_dialog(entity_obj)
                    print(f"  Berhasil meninggalkan: \"{title_to_leave}\"")
                except errors.FloodWaitError as e:
                    wait_duration = e.seconds + FLOOD_WAIT_BUFFER
                    print(f"  Terkena FloodWaitError: Perlu menunggu {e.seconds} dtk. Akan tidur selama {wait_duration} dtk.")
                    await asyncio.sleep(wait_duration)
                    print(f"  Selesai menunggu. Item \"{title_to_leave}\" ini mungkin belum selesai. Lanjut ke item berikutnya.")
                    continue 
                except Exception as e:
                    print(f"  Gagal meninggalkan \"{title_to_leave}\": {type(e).__name__} - {e}")
                print(f"  Menunggu {NORMAL_ACTION_DELAY} detik sebelum item berikutnya...")
                await asyncio.sleep(NORMAL_ACTION_DELAY)

        # --- Fase 2: Hapus Obrolan Bot ---
        print("\n--- FASE 2: HAPUS OBROLAN DENGAN BOT ---")
        if not bots_to_process:
            print("Tidak ada bot yang perlu diproses (setelah filter whitelist).")
        else:
            print(f"Mode Otomatis: Akan mencoba memblokir & menghapus {len(bots_to_process)} bot.")
            for bot_entity in bots_to_process:
                bot_name_to_delete = bot_entity.first_name if hasattr(bot_entity, 'first_name') else (f"@{bot_entity.username}" if hasattr(bot_entity, 'username') else f"Bot ID:{bot_entity.id}")
                print(f"Memproses bot: \"{bot_name_to_delete}\"...")
                try:
                    print(f"  Mencoba memblokir \"{bot_name_to_delete}\"...")
                    await client(functions.contacts.BlockRequest(id=bot_entity.id))
                    print(f"    Berhasil memblokir.")
                    
                    print(f"  Mencoba menghapus obrolan dengan \"{bot_name_to_delete}\"...")
                    await client.delete_dialog(bot_entity)
                    print(f"    Berhasil menghapus obrolan.")
                except errors.FloodWaitError as e:
                    wait_duration = e.seconds + FLOOD_WAIT_BUFFER
                    print(f"  Terkena FloodWaitError saat memproses \"{bot_name_to_delete}\": Perlu menunggu {e.seconds} dtk. Akan tidur selama {wait_duration} dtk.")
                    await asyncio.sleep(wait_duration)
                    print(f"  Selesai menunggu. Bot \"{bot_name_to_delete}\" ini mungkin belum selesai diproses sepenuhnya. Lanjut ke bot berikutnya.")
                    continue 
                except errors.UserIsBlockedError:
                     print(f"  Info: \"{bot_name_to_delete}\" sudah diblokir sebelumnya. Mencoba menghapus obrolan...")
                     try:
                         await client.delete_dialog(bot_entity)
                         print(f"    Berhasil menghapus obrolan yang sudah diblokir.")
                     except Exception as e_del:
                         print(f"    Gagal menghapus obrolan (setelah blokir): {type(e_del).__name__} - {e_del}")
                except Exception as e:
                    print(f"  Gagal memproses bot \"{bot_name_to_delete}\": {type(e).__name__} - {e}")
                
                print(f"  Menunggu {NORMAL_ACTION_DELAY} detik sebelum item berikutnya...")
                await asyncio.sleep(NORMAL_ACTION_DELAY) 

        print('\nSemua proses otomatis telah selesai.')

    except errors.PhoneNumberInvalidError:
        print("Kesalahan: Format nomor telepon tidak valid. Harap jalankan lagi dan masukkan dengan benar.")
    except errors.PhoneCodeInvalidError:
        print("Kesalahan: Kode verifikasi yang Anda masukkan salah. Harap jalankan lagi.")
    except errors.PhoneCodeExpiredError:
        print("Kesalahan: Kode verifikasi sudah kedaluwarsa. Silakan jalankan lagi.")
    except errors.SessionPasswordNeededError:
         print("Kesalahan: Kata sandi Two-Factor Authentication (2FA) diperlukan atau salah. Harap jalankan lagi.")
    except Exception as e:
        print(f"Terjadi kesalahan umum yang tidak terduga: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc() # Cetak traceback untuk debug lebih lanjut
    finally:
        if client.is_connected():
            print("Memutus koneksi ke Telegram...")
            await client.disconnect()
        print("Skrip selesai.")

if __name__ == '__main__':
    asyncio.run(main())
