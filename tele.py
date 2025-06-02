import asyncio
import os
import time # Meskipun tidak digunakan secara aktif, mungkin berguna di masa depan
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession # Import ini bisa dihapus jika tidak ada rencana StringSession
from dotenv import load_dotenv
import traceback

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

# --- KONFIGURASI EKSEKUSI ---
AUTOMATIC_PROCESS_ALL = True # True untuk proses otomatis, False untuk konfirmasi manual
NORMAL_ACTION_DELAY = 5      # Detik menunggu antar aksi normal
FLOOD_WAIT_BUFFER = 15     # Detik buffer tambahan saat terkena FloodWaitError
# -----------------------------------------

load_dotenv()

API_ID_STR = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

def initialize_env_vars():
    """Memeriksa dan menginisialisasi variabel lingkungan."""
    if not API_ID_STR or not API_HASH:
        print(f"{C.BOLD}{C.RED}Kesalahan Kritis: TELEGRAM_API_ID atau TELEGRAM_API_HASH tidak ditemukan di file .env.{C.RESET}")
        print(f"{C.RED}Pastikan file .env ada di direktori yang sama dengan skrip dan berisi variabel tersebut.{C.RESET}")
        print(f"{C.RED}Contoh isi .env:\nTELEGRAM_API_ID=1234567\nTELEGRAM_API_HASH=abcdef1234567890abcdef1234567890{C.RESET}")
        exit(1)
    try:
        api_id = int(API_ID_STR)
        return api_id, API_HASH
    except ValueError:
        print(f"{C.BOLD}{C.RED}Kesalahan Kritis: TELEGRAM_API_ID ('{API_ID_STR}') harus berupa angka integer.{C.RESET}")
        exit(1)

API_ID, API_HASH = initialize_env_vars()

SESSION_FILE_NAME = 'my_telegram_session.session'
WHITELIST_FILE_PATH = 'whitelist.txt'

def load_whitelist_usernames():
    """Memuat daftar username dari file whitelist."""
    usernames = []
    print(f"\n{C.CYAN}Membaca file whitelist: {C.BOLD}{WHITELIST_FILE_PATH}{C.RESET}")
    try:
        if os.path.exists(WHITELIST_FILE_PATH):
            with open(WHITELIST_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    username = line.strip().lower()
                    if username and not username.startswith('#'): # Abaikan baris komentar
                        usernames.append(username)
            
            if usernames:
                print(f"  {C.GREEN}Berhasil memuat {C.BOLD}{len(usernames)}{C.RESET}{C.GREEN} username dari whitelist.{C.RESET}")
                # print(f"  {C.BLUE}Username di whitelist: {', '.join(usernames)}{C.RESET}") # Uncomment untuk debug
            else:
                print(f"  {C.YELLOW}File whitelist ditemukan namun kosong atau hanya berisi komentar.{C.RESET}")
        else:
            print(f"  {C.YELLOW}Peringatan: File whitelist '{WHITELIST_FILE_PATH}' tidak ditemukan. Tidak ada username yang di-whitelist.{C.RESET}")
    except Exception as e:
        print(f"  {C.RED}Error saat memuat whitelist: {e}{C.RESET}")
    return usernames

async def main():
    print(f"{C.BOLD}{C.MAGENTA}==============================================={C.RESET}")
    print(f"{C.BOLD}{C.MAGENTA}=== SKRIP MANAJEMEN AKUN TELEGRAM v12 ==={C.RESET}")
    print(f"{C.BOLD}{C.MAGENTA}==============================================={C.RESET}")
    
    if AUTOMATIC_PROCESS_ALL:
        print(f"\n{C.CYAN}[MODE OTOMATIS AKTIF]{C.RESET}{C.YELLOW} Skrip akan memproses semua item non-whitelist tanpa konfirmasi tambahan setelah login.{C.RESET}")
    else:
        print(f"\n{C.CYAN}[MODE MANUAL AKTIF]{C.RESET}{C.YELLOW} Skrip akan meminta konfirmasi sebelum memproses item.{C.RESET}")

    lower_case_whitelist_usernames = load_whitelist_usernames()

    # Menggunakan file sesi default Telethon. Tidak perlu fungsi loadSession() kustom.
    client = TelegramClient(SESSION_FILE_NAME, API_ID, API_HASH,
                            retry_delay=10,
                            connection_retries=5)

    print(f"\n{C.CYAN}Menghubungkan ke Telegram...{C.RESET}")
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"  {C.YELLOW}Sesi tidak terotorisasi. Memulai proses login interaktif...{C.RESET}")
            phone_number = input(f"  {C.WHITE}Masukkan nomor telepon Anda (format +62xxxx): {C.RESET}").strip()
            await client.send_code_request(phone_number)
            try:
                code = input(f"  {C.WHITE}Masukkan kode OTP yang Anda terima: {C.RESET}").strip()
                await client.sign_in(phone_number, code)
            except errors.SessionPasswordNeededError:
                password = input(f"  {C.WHITE}Masukkan kata sandi Two-Factor Authentication (2FA): {C.RESET}").strip()
                await client.sign_in(password=password)
            print(f"  {C.GREEN}Login berhasil! Sesi disimpan di {C.BOLD}{SESSION_FILE_NAME}{C.RESET}")
        
        me = await client.get_me()
        print(f"\n{C.GREEN}Berhasil terhubung sebagai: {C.BOLD}{me.first_name or ''} {me.last_name or ''}{C.RESET}{C.GREEN} (@{me.username if me.username else 'Tanpa Username'}){C.RESET}")
        print(f"{C.BLUE}-----------------------------------------------{C.RESET}")

        if not AUTOMATIC_PROCESS_ALL:
            lanjut_input = input(f"\n{C.YELLOW}Lanjutkan untuk memproses grup/channel dan bot? (y/n): {C.RESET}").lower().strip()
            if lanjut_input != 'y':
                print(f'{C.YELLOW}Proses dibatalkan oleh pengguna.{C.RESET}')
                return
        else:
            print(f"\n{C.CYAN}Melanjutkan proses secara otomatis...{C.RESET}")

        print(f"\n{C.CYAN}Mengumpulkan daftar dialog (chat)... Mohon tunggu, ini mungkin butuh beberapa saat.{C.RESET}")
        all_dialogs_api = []
        async for dialog in client.iter_dialogs():
            all_dialogs_api.append(dialog)
        print(f"  {C.GREEN}Selesai mengumpulkan {C.BOLD}{len(all_dialogs_api)}{C.RESET}{C.GREEN} dialog.{C.RESET}")
        
        groups_channels_to_process_entities = []
        bots_to_process_entities = []
        whitelisted_dialogs_log_ids = set() # Untuk mencatat ID dialog yang di-whitelist agar tidak berulang kali dicetak

        print(f"\n{C.CYAN}Memfilter dialog dan menerapkan whitelist...{C.RESET}")
        for i, dialog in enumerate(all_dialogs_api):
            entity = dialog.entity
            title = dialog.title if hasattr(dialog, 'title') else "Tanpa Judul"
            username = None
            is_bot_flag = False

            if hasattr(entity, 'username') and entity.username:
                username = entity.username.lower()
            
            if isinstance(entity, types.User) and entity.bot:
                is_bot_flag = True

            display_title = title if title != "Tanpa Judul" else (f"@{username}" if username else f"ID:{entity.id}")

            # Log setiap dialog yang diperiksa (opsional, bisa di-uncomment untuk detail)
            # print(f"  Memeriksa ({i+1}/{len(all_dialogs_api)}): \"{C.BOLD}{display_title}{C.RESET}\" (Bot: {is_bot_flag}, Username: {username})")

            is_whitelisted = False
            if username and username in lower_case_whitelist_usernames:
                is_whitelisted = True
            
            if is_whitelisted:
                if dialog.id not in whitelisted_dialogs_log_ids: # Hanya cetak sekali per item whitelist
                    print(f"    {C.BLUE}↳ [WHITELIST] \"{C.BOLD}{display_title}{C.RESET}{C.BLUE}\" akan dilewati.{C.RESET}")
                    whitelisted_dialogs_log_ids.add(dialog.id)
                continue 
            
            # Jika tidak di-whitelist, tambahkan ke daftar proses
            if is_bot_flag:
                bots_to_process_entities.append(dialog.entity)
            elif dialog.is_group or dialog.is_channel:
                groups_channels_to_process_entities.append(dialog.entity)

        if whitelisted_dialogs_log_ids:
            print(f"  {C.GREEN}Total {C.BOLD}{len(whitelisted_dialogs_log_ids)}{C.RESET}{C.GREEN} item terdeteksi dalam whitelist dan tidak akan diproses.{C.RESET}")
        else:
            print(f"  {C.YELLOW}Tidak ada item dalam dialog yang cocok dengan whitelist (atau whitelist kosong).{C.RESET}")


        # --- Fase 1: Keluar dari Grup/Channel ---
        print(f"\n{C.BOLD}{C.MAGENTA}--- FASE 1: KELUAR DARI GRUP/CHANNEL ---{C.RESET}")
        if not groups_channels_to_process_entities:
            print(f"  {C.YELLOW}Tidak ada grup/channel yang perlu diproses (setelah filter whitelist).{C.RESET}")
        else:
            print(f"  {C.CYAN}Akan memproses {C.BOLD}{len(groups_channels_to_process_entities)}{C.RESET}{C.CYAN} grup/channel (non-whitelist).{C.RESET}")
            for idx, entity_obj in enumerate(groups_channels_to_process_entities):
                title_to_leave = entity_obj.title if hasattr(entity_obj, 'title') else (f"@{entity_obj.username}" if hasattr(entity_obj, 'username') and entity_obj.username else f"ID:{entity_obj.id}")
                print(f"\n  ({idx+1}/{len(groups_channels_to_process_entities)}) Memproses: \"{C.BOLD}{title_to_leave}{C.RESET}\"")
                try:
                    print(f"    {C.CYAN}↳ Mencoba meninggalkan...{C.RESET}")
                    await client.delete_dialog(entity_obj) # Untuk grup/channel, ini berarti "leave"
                    print(f"    {C.GREEN}↳ [BERHASIL] Meninggalkan \"{title_to_leave}\".{C.RESET}")
                except errors.FloodWaitError as e:
                    wait_duration = e.seconds + FLOOD_WAIT_BUFFER
                    print(f"    {C.YELLOW}↳ [FLOOD WAIT] Terkena FloodWaitError. Perlu menunggu {e.seconds} dtk.{C.RESET}")
                    print(f"    {C.YELLOW}↳ Akan tidur selama {wait_duration} dtk untuk pemulihan...{C.RESET}")
                    await asyncio.sleep(wait_duration)
                    print(f"    {C.YELLOW}↳ Selesai menunggu. Item \"{title_to_leave}\" ini mungkin {C.BOLD}belum{C.RESET}{C.YELLOW} selesai diproses. Lanjut ke item berikutnya.{C.RESET}")
                    continue 
                except Exception as e:
                    print(f"    {C.RED}↳ [GAGAL] Meninggalkan \"{title_to_leave}\": {type(e).__name__} - {e}{C.RESET}")
                
                if idx < len(groups_channels_to_process_entities) - 1: # Jangan sleep setelah item terakhir
                    print(f"    {C.CYAN}↳ Menunggu {NORMAL_ACTION_DELAY} detik sebelum item berikutnya...{C.RESET}")
                    await asyncio.sleep(NORMAL_ACTION_DELAY)

        # --- Fase 2: Hapus Obrolan & Blokir Bot ---
        print(f"\n{C.BOLD}{C.MAGENTA}--- FASE 2: HAPUS OBROLAN & BLOKIR BOT ---{C.RESET}")
        if not bots_to_process_entities:
            print(f"  {C.YELLOW}Tidak ada bot yang perlu diproses (setelah filter whitelist).{C.RESET}")
        else:
            print(f"  {C.CYAN}Akan memproses {C.BOLD}{len(bots_to_process_entities)}{C.RESET}{C.CYAN} bot (non-whitelist).{C.RESET}")
            for idx, bot_entity in enumerate(bots_to_process_entities):
                bot_name_to_process = bot_entity.first_name if hasattr(bot_entity, 'first_name') and bot_entity.first_name else (f"@{bot_entity.username}" if hasattr(bot_entity, 'username') and bot_entity.username else f"Bot ID:{bot_entity.id}")
                print(f"\n  ({idx+1}/{len(bots_to_process_entities)}) Memproses bot: \"{C.BOLD}{bot_name_to_process}{C.RESET}\"")
                try:
                    # 1. Blokir Bot
                    try:
                        print(f"    {C.CYAN}↳ Mencoba memblokir \"{bot_name_to_process}\"...{C.RESET}")
                        await client(functions.contacts.BlockRequest(id=bot_entity.id))
                        print(f"    {C.GREEN}↳ [BERHASIL] Memblokir bot.{C.RESET}")
                    except errors.UserIsBlockedError:
                        print(f"    {C.BLUE}↳ [INFO] Bot \"{bot_name_to_process}\" sudah diblokir sebelumnya.{C.RESET}")
                    except Exception as e_block: # Tangani error blokir lainnya
                        print(f"    {C.RED}↳ [GAGAL BLOKIR] Gagal memblokir \"{bot_name_to_process}\": {type(e_block).__name__} - {e_block}{C.RESET}")
                        # Tetap lanjut mencoba hapus dialog meskipun blokir gagal
                    
                    # 2. Hapus Dialog dengan Bot
                    print(f"    {C.CYAN}↳ Mencoba menghapus obrolan dengan \"{bot_name_to_process}\"...{C.RESET}")
                    await client.delete_dialog(bot_entity)
                    print(f"    {C.GREEN}↳ [BERHASIL] Menghapus obrolan.{C.RESET}")

                except errors.FloodWaitError as e:
                    wait_duration = e.seconds + FLOOD_WAIT_BUFFER
                    print(f"    {C.YELLOW}↳ [FLOOD WAIT] Terkena FloodWaitError saat memproses \"{bot_name_to_process}\". Perlu menunggu {e.seconds} dtk.{C.RESET}")
                    print(f"    {C.YELLOW}↳ Akan tidur selama {wait_duration} dtk untuk pemulihan...{C.RESET}")
                    await asyncio.sleep(wait_duration)
                    print(f"    {C.YELLOW}↳ Selesai menunggu. Bot \"{bot_name_to_process}\" ini mungkin {C.BOLD}belum{C.RESET}{C.YELLOW} selesai diproses sepenuhnya. Lanjut ke bot berikutnya.{C.RESET}")
                    continue
                except Exception as e: # Error umum saat memproses bot (selain FloodWait)
                    print(f"    {C.RED}↳ [GAGAL PROSES] Gagal memproses bot \"{bot_name_to_process}\": {type(e).__name__} - {e}{C.RESET}")

                if idx < len(bots_to_process_entities) - 1: # Jangan sleep setelah item terakhir
                    print(f"    {C.CYAN}↳ Menunggu {NORMAL_ACTION_DELAY} detik sebelum item berikutnya...{C.RESET}")
                    await asyncio.sleep(NORMAL_ACTION_DELAY)

        print(f"\n{C.BOLD}{C.GREEN}==============================================={C.RESET}")
        print(f"{C.BOLD}{C.GREEN}=== Semua proses otomatis telah selesai. ==={C.RESET}")
        print(f"{C.BOLD}{C.GREEN}==============================================={C.RESET}")

    except errors.PhoneNumberInvalidError:
        print(f"{C.BOLD}{C.RED}Kesalahan Login: Format nomor telepon tidak valid. Harap periksa dan jalankan lagi.{C.RESET}")
    except errors.PhoneCodeInvalidError:
        print(f"{C.BOLD}{C.RED}Kesalahan Login: Kode verifikasi (OTP) yang Anda masukkan salah. Harap jalankan lagi.{C.RESET}")
    except errors.PhoneCodeExpiredError:
        print(f"{C.BOLD}{C.RED}Kesalahan Login: Kode verifikasi (OTP) sudah kedaluwarsa. Silakan jalankan lagi.{C.RESET}")
    except errors.SessionPasswordNeededError: # Jika input password 2FA salah saat login
        print(f"{C.BOLD}{C.RED}Kesalahan Login: Kata sandi Two-Factor Authentication (2FA) salah. Harap jalankan lagi.{C.RESET}")
    except errors.rpcerrorlist.ApiIdInvalidError:
        print(f"{C.BOLD}{C.RED}Kesalahan Kritis: TELEGRAM_API_ID atau TELEGRAM_API_HASH tidak valid. Periksa kembali di my.telegram.org.{C.RESET}")
    except ConnectionError:
        print(f"{C.BOLD}{C.RED}Kesalahan Koneksi: Tidak dapat terhubung ke server Telegram. Periksa koneksi internet Anda.{C.RESET}")
    except Exception as e:
        print(f"{C.BOLD}{C.RED}Terjadi kesalahan umum yang tidak terduga:{C.RESET}")
        print(f"{C.RED}  Tipe Error : {type(e).__name__}{C.RESET}")
        print(f"{C.RED}  Pesan Error: {e}{C.RESET}")
        print(f"{C.YELLOW}Detail Traceback:{C.RESET}")
        traceback.print_exc() # Mencetak traceback untuk debug
    finally:
        if client.is_connected():
            print(f"\n{C.CYAN}Memutus koneksi ke Telegram...{C.RESET}")
            await client.disconnect()
            print(f"  {C.GREEN}Koneksi berhasil diputus.{C.RESET}")
        print(f"\n{C.BOLD}{C.MAGENTA}Skrip selesai dijalankan.{C.RESET}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{C.YELLOW}Proses dihentikan oleh pengguna (Ctrl+C).{C.RESET}")
    except Exception as e: # Menangkap exception yang mungkin terjadi di luar loop asyncio utama
        print(f"{C.BOLD}{C.RED}Error tak terduga di luar loop utama: {type(e).__name__} - {e}{C.RESET}")
        traceback.print_exc()
