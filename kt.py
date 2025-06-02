import asyncio
import os
import time
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession
from dotenv import load_dotenv

# --- WARNA UNTUK OUTPUT TERMINAL ---
class C: # Colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
# ------------------------------------

# --- KONFIGURASI EKSEKUSI OTOMATIS ---
AUTOMATIC_PROCESS_ALL = True
NORMAL_ACTION_DELAY = 5 
FLOOD_WAIT_BUFFER = 15
# -----------------------------------------

load_dotenv()

API_ID_STR = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

if not API_ID_STR or not API_HASH:
    print(f"{C.BOLD}{C.RED}Kesalahan: TELEGRAM_API_ID atau TELEGRAM_API_HASH tidak ditemukan di file .env.{C.RESET}")
    print(f"{C.RED}Pastikan file .env sudah benar dan berisi variabel tersebut.{C.RESET}")
    exit(1)

try:
    API_ID = int(API_ID_STR)
except ValueError:
    print(f"{C.BOLD}{C.RED}Kesalahan: TELEGRAM_API_ID ('{API_ID_STR}') harus berupa angka.{C.RESET}")
    exit(1)

SESSION_FILE_NAME = 'my_telegram_session.session'
WHITELIST_FILE_PATH = 'whitelist.txt'

def load_whitelist_usernames():
    usernames = []
    try:
        if os.path.exists(WHITELIST_FILE_PATH):
            print(f"{C.CYAN}Memuat whitelist usernames dari {C.BOLD}{WHITELIST_FILE_PATH}{C.RESET}{C.CYAN}...{C.RESET}")
            with open(WHITELIST_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    username = line.strip().lower()
                    if username:
                        usernames.append(username)
            if usernames:
                print(f"{C.GREEN}{len(usernames)} username berhasil dimuat dari whitelist.{C.RESET}")
            else:
                print(f"{C.YELLOW}File whitelist '{WHITELIST_FILE_PATH}' ditemukan, tetapi kosong.{C.RESET}")
        else:
            print(f"{C.YELLOW}Peringatan: File whitelist '{WHITELIST_FILE_PATH}' tidak ditemukan. Tidak ada username yang di-whitelist.{C.RESET}")
    except Exception as e:
        print(f"{C.YELLOW}Peringatan: Gagal memuat whitelist dari '{WHITELIST_FILE_PATH}': {e}{C.RESET}")
    return usernames

def loadSession():
  try:
    if os.path.exists(SESSION_FILE_PATH):
      print(f"{C.CYAN}Memuat sesi dari {C.BOLD}{SESSION_FILE_PATH}{C.RESET}{C.CYAN}...{C.RESET}")
      return fs.readFileSync(SESSION_FILE_PATH, 'utf8') # Seharusnya tidak ada 'fs' di sini jika ini Python

  except NameError: # Tangani jika fs tidak terdefinisi
      pass # Telethon yang akan menangani sesi file
  except Exception as e:
    print(f"{C.YELLOW}Peringatan: Tidak dapat memuat file sesi secara manual (Telethon akan mencoba): {e}{C.RESET}")
  return '' # Default jika tidak ada sesi string eksplisit (Telethon pakai file)


async def main():
    print(f"{C.BOLD}{C.MAGENTA}Memulai skrip Telegram (v11 - Output Berwarna)...{C.RESET}")
    if AUTOMATIC_PROCESS_ALL:
        print(f"{C.CYAN}MODE OTOMATIS AKTIF: Akan memproses semua item non-whitelist.{C.RESET}")
    
    lower_case_whitelist_usernames = load_whitelist_usernames()

    client = TelegramClient(SESSION_FILE_NAME, API_ID, API_HASH, 
                            retry_delay=10,
                            connection_retries=5)

    print(f"{C.CYAN}Mencoba menghubungkan ke Telegram...{C.RESET}")
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"{C.YELLOW}Sesi tidak terotorisasi. Memulai proses login (membutuhkan input manual)...{C.RESET}")
            # Input login dari Telethon tidak bisa diwarnai langsung dari sini
            phone_number = input('Masukkan nomor telepon Anda (format +62xxxx): ')
            await client.send_code_request(phone_number)
            try:
                await client.sign_in(phone_number, input('Masukkan kode yang Anda terima: '))
            except errors.SessionPasswordNeededError:
                await client.sign_in(password=input('Masukkan kata sandi Two-Factor Authentication (2FA) Anda: '))
            print(f"{C.GREEN}Login berhasil, file sesi telah dibuat/diperbarui.{C.RESET}")
        
        me = await client.get_me()
        print(f"\n{C.GREEN}Berhasil terhubung sebagai: {C.BOLD}{me.first_name}{C.RESET}{C.GREEN} (@{me.username if me.username else 'Tanpa Username'}){C.RESET}")
        print(f"{C.BLUE}---{C.RESET}\n")

        if not AUTOMATIC_PROCESS_ALL: # Blok ini tidak akan berjalan jika AUTOMATIC_PROCESS_ALL = True
            lanjut_input = input('Lanjutkan untuk mendapatkan daftar grup/channel dan memilih mana yang akan ditinggalkan? (y/n): ').lower()
            if lanjut_input != 'y':
                print(f'{C.YELLOW}Proses dibatalkan oleh pengguna.{C.RESET}')
                return
        else:
            print(f"{C.CYAN}Melanjutkan proses secara otomatis...{C.RESET}")

        print(f'{C.CYAN}\nMengumpulkan daftar dialog... Mohon tunggu...{C.RESET}')
        all_dialogs_api = []
        async for dialog in client.iter_dialogs():
            all_dialogs_api.append(dialog)
        
        groups_channels_to_process_entities = []
        bots_to_process_entities = []
        whitelisted_dialogs_log_ids = set()

        print(f"{C.CYAN}Memfilter dialog dan menerapkan whitelist...{C.RESET}")
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
                    print(f"   {C.BLUE}-> \"{display_title}\" ada di WHITELIST, akan dilewati.{C.RESET}")
                    whitelisted_dialogs_log_ids.add(dialog.id)
                continue 

            if is_bot_flag:
                bots_to_process_entities.append(dialog.entity)
            elif dialog.is_group or dialog.is_channel:
                groups_channels_to_process_entities.append(dialog.entity)

        if whitelisted_dialogs_log_ids:
            print(f"\n{C.BLUE}Total {len(whitelisted_dialogs_log_ids)} item terdeteksi dalam whitelist dan tidak akan diproses.{C.RESET}")

        # --- Fase 1: Keluar dari Grup/Channel ---
        print(f"\n{C.BOLD}{C.MAGENTA}--- FASE 1: KELUAR DARI GRUP/CHANNEL ---{C.RESET}")
        if not groups_channels_to_process_entities:
            print(f"{C.YELLOW}Tidak ada grup/channel yang perlu diproses (setelah filter whitelist).{C.RESET}")
        else:
            print(f"{C.CYAN}Mode Otomatis: Akan mencoba keluar dari {len(groups_channels_to_process_entities)} grup/channel.{C.RESET}")
            for entity_obj in groups_channels_to_process_entities:
                title_to_leave = entity_obj.title if hasattr(entity_obj, 'title') else (f"@{entity_obj.username}" if hasattr(entity_obj, 'username') else f"ID:{entity_obj.id}")
                print(f"Mencoba meninggalkan: \"{C.BOLD}{title_to_leave}{C.RESET}\"...")
                try:
                    await client.delete_dialog(entity_obj)
                    print(f"  {C.GREEN}Berhasil meninggalkan: \"{title_to_leave}\"{C.RESET}")
                except errors.FloodWaitError as e:
                    wait_duration = e.seconds + FLOOD_WAIT_BUFFER
                    print(f"  {C.YELLOW}Terkena FloodWaitError: Perlu menunggu {e.seconds} dtk. Akan tidur selama {wait_duration} dtk.{C.RESET}")
                    await asyncio.sleep(wait_duration)
                    print(f"  {C.YELLOW}Selesai menunggu. Item \"{title_to_leave}\" ini mungkin belum selesai. Lanjut ke item berikutnya.{C.RESET}")
                    continue 
                except Exception as e:
                    print(f"  {C.RED}Gagal meninggalkan \"{title_to_leave}\": {type(e).__name__} - {e}{C.RESET}")
                print(f"  {C.CYAN}Menunggu {NORMAL_ACTION_DELAY} detik sebelum item berikutnya...{C.RESET}")
                await asyncio.sleep(NORMAL_ACTION_DELAY)

        # --- Fase 2: Hapus Obrolan Bot ---
        print(f"\n{C.BOLD}{C.MAGENTA}--- FASE 2: HAPUS OBROLAN DENGAN BOT ---{C.RESET}")
        if not bots_to_process_entities:
            print(f"{C.YELLOW}Tidak ada bot yang perlu diproses (setelah filter whitelist).{C.RESET}")
        else:
            print(f"{C.CYAN}Mode Otomatis: Akan mencoba memblokir & menghapus {len(bots_to_process_entities)} bot.{C.RESET}")
            for bot_entity in bots_to_process_entities:
                bot_name_to_delete = bot_entity.first_name if hasattr(bot_entity, 'first_name') else (f"@{bot_entity.username}" if hasattr(bot_entity, 'username') else f"Bot ID:{bot_entity.id}")
                print(f"Memproses bot: \"{C.BOLD}{bot_name_to_delete}{C.RESET}\"...")
                try:
                    print(f"  Mencoba memblokir \"{bot_name_to_delete}\"...")
                    await client(functions.contacts.BlockRequest(id=bot_entity.id))
                    print(f"    {C.GREEN}Berhasil memblokir.{C.RESET}")
                    
                    print(f"  Mencoba menghapus obrolan dengan \"{bot_name_to_delete}\"...")
                    await client.delete_dialog(bot_entity)
                    print(f"    {C.GREEN}Berhasil menghapus obrolan.{C.RESET}")
                except errors.FloodWaitError as e:
                    wait_duration = e.seconds + FLOOD_WAIT_BUFFER
                    print(f"  {C.YELLOW}Terkena FloodWaitError saat memproses \"{bot_name_to_delete}\": Perlu menunggu {e.seconds} dtk. Akan tidur selama {wait_duration} dtk.{C.RESET}")
                    await asyncio.sleep(wait_duration)
                    print(f"  {C.YELLOW}Selesai menunggu. Bot \"{bot_name_to_delete}\" ini mungkin belum selesai diproses sepenuhnya. Lanjut ke bot berikutnya.{C.RESET}")
                    continue 
                except errors.UserIsBlockedError:
                     print(f"  {C.BLUE}Info: \"{bot_name_to_delete}\" sudah diblokir sebelumnya. Mencoba menghapus obrolan...{C.RESET}")
                     try:
                         await client.delete_dialog(bot_entity)
                         print(f"    {C.GREEN}Berhasil menghapus obrolan yang sudah diblokir.{C.RESET}")
                     except Exception as e_del:
                         print(f"    {C.RED}Gagal menghapus obrolan (setelah blokir): {type(e_del).__name__} - {e_del}{C.RESET}")
                except Exception as e:
                    print(f"  {C.RED}Gagal memproses bot \"{bot_name_to_delete}\": {type(e).__name__} - {e}{C.RESET}")
                
                print(f"  {C.CYAN}Menunggu {NORMAL_ACTION_DELAY} detik sebelum item berikutnya...{C.RESET}")
                await asyncio.sleep(NORMAL_ACTION_DELAY) 

        print(f'\n{C.BOLD}{C.GREEN}Semua proses otomatis telah selesai.{C.RESET}')

    except errors.PhoneNumberInvalidError:
        print(f"{C.BOLD}{C.RED}Kesalahan: Format nomor telepon tidak valid. Harap jalankan lagi dan masukkan dengan benar.{C.RESET}")
    except errors.PhoneCodeInvalidError:
        print(f"{C.BOLD}{C.RED}Kesalahan: Kode verifikasi yang Anda masukkan salah. Harap jalankan lagi.{C.RESET}")
    except errors.PhoneCodeExpiredError:
        print(f"{C.BOLD}{C.RED}Kesalahan: Kode verifikasi sudah kedaluwarsa. Silakan jalankan lagi.{C.RESET}")
    except errors.SessionPasswordNeededError:
         print(f"{C.BOLD}{C.RED}Kesalahan: Kata sandi Two-Factor Authentication (2FA) diperlukan atau salah. Harap jalankan lagi.{C.RESET}")
    except Exception as e:
        print(f"{C.BOLD}{C.RED}Terjadi kesalahan umum yang tidak terduga: {type(e).__name__} - {e}{C.RESET}")
        import traceback
        traceback.print_exc() 
    finally:
        if client.is_connected():
            print(f"{C.CYAN}Memutus koneksi ke Telegram...{C.RESET}")
            await client.disconnect()
        print(f"{C.BOLD}{C.MAGENTA}Skrip selesai.{C.RESET}")

if __name__ == '__main__':
    asyncio.run(main())
