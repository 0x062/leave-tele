import asyncio
import os
from telethon import TelegramClient, errors, functions, types
from dotenv import load_dotenv
import traceback

# --- WARNA UNTUK OUTPUT TERMINAL ---
class C: # Colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'      # Merah Cerah
    GREEN = '\033[92m'    # Hijau Cerah
    YELLOW = '\033[93m'   # Kuning Cerah
    BLUE = '\033[94m'     # Biru Cerah
    MAGENTA = '\033[95m'  # Magenta Cerah
    CYAN = '\033[96m'     # Cyan Cerah
    WHITE = '\033[97m'    # Putih Cerah
# ------------------------------------

# --- KONFIGURASI EKSEKUSI ---
AUTOMATIC_PROCESS_ALL = True
NORMAL_ACTION_DELAY = 5
FLOOD_WAIT_BUFFER = 15
# -----------------------------------------

load_dotenv()

API_ID_STR = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

def initialize_env_vars():
    if not API_ID_STR or not API_HASH:
        print(f"{C.BOLD}{C.RED}Kesalahan Kritis: TELEGRAM_API_ID atau TELEGRAM_API_HASH tidak ditemukan di file .env.{C.RESET}")
        print(f"{C.RED}Pastikan file .env ada dan berisi variabel tersebut.{C.RESET}")
        print(f"{C.RED}Contoh .env:\nTELEGRAM_API_ID=1234567\nTELEGRAM_API_HASH=abcdef1234567890abcdef1234567890{C.RESET}")
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
    usernames = []
    print(f"\n{C.BOLD}{C.CYAN}Membaca file whitelist: {C.BOLD}{WHITELIST_FILE_PATH}{C.RESET}")
    try:
        if os.path.exists(WHITELIST_FILE_PATH):
            with open(WHITELIST_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    username = line.strip().lower()
                    if username and not username.startswith('#'):
                        usernames.append(username)
            if usernames:
                print(f"  {C.BOLD}{C.GREEN}Berhasil memuat {C.BOLD}{len(usernames)}{C.GREEN} username dari whitelist.{C.RESET}")
            else:
                print(f"  {C.BOLD}{C.YELLOW}File whitelist ditemukan namun kosong atau hanya berisi komentar.{C.RESET}")
        else:
            print(f"  {C.BOLD}{C.YELLOW}Peringatan: File whitelist '{WHITELIST_FILE_PATH}' tidak ditemukan.{C.RESET}")
    except Exception as e:
        print(f"  {C.BOLD}{C.RED}Error saat memuat whitelist: {e}{C.RESET}")
    return usernames

async def main():
    print(f"{C.BOLD}{C.MAGENTA}==============================================={C.RESET}")
    print(f"{C.BOLD}{C.MAGENTA}=== SKRIP MANAJEMEN AKUN TELEGRAM v13.1 (Warna Ditingkatkan) ==={C.RESET}")
    print(f"{C.BOLD}{C.MAGENTA}==============================================={C.RESET}")
    
    if AUTOMATIC_PROCESS_ALL:
        print(f"\n{C.BOLD}{C.CYAN}[MODE OTOMATIS AKTIF]{C.RESET}{C.BOLD}{C.YELLOW} Skrip akan memproses semua item non-whitelist tanpa konfirmasi.{C.RESET}")
    else:
        print(f"\n{C.BOLD}{C.CYAN}[MODE MANUAL AKTIF]{C.RESET}{C.BOLD}{C.YELLOW} Skrip akan meminta konfirmasi sebelum memproses.{C.RESET}")

    lower_case_whitelist_usernames = load_whitelist_usernames()

    client = TelegramClient(SESSION_FILE_NAME, API_ID, API_HASH, retry_delay=10, connection_retries=5)

    print(f"\n{C.BOLD}{C.CYAN}Menghubungkan ke Telegram...{C.RESET}")
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"  {C.BOLD}{C.YELLOW}Sesi tidak terotorisasi. Memulai proses login interaktif...{C.RESET}")
            phone_number = input(f"  {C.BOLD}{C.WHITE}Masukkan nomor telepon Anda (format +62xxxx): {C.RESET}").strip()
            await client.send_code_request(phone_number)
            try:
                code = input(f"  {C.BOLD}{C.WHITE}Masukkan kode OTP yang Anda terima: {C.RESET}").strip()
                await client.sign_in(phone_number, code)
            except errors.SessionPasswordNeededError:
                password = input(f"  {C.BOLD}{C.WHITE}Masukkan kata sandi Two-Factor Authentication (2FA): {C.RESET}").strip()
                await client.sign_in(password=password)
            print(f"  {C.BOLD}{C.GREEN}Login berhasil! Sesi disimpan di {C.BOLD}{SESSION_FILE_NAME}{C.RESET}")
        
        me = await client.get_me()
        print(f"\n{C.BOLD}{C.GREEN}Berhasil terhubung sebagai: {C.BOLD}{me.first_name or ''} {me.last_name or ''}{C.RESET} {C.BOLD}{C.GREEN}(@{me.username if me.username else 'Tanpa Username'}){C.RESET}")
        print(f"{C.BOLD}{C.BLUE}-----------------------------------------------{C.RESET}")

        if not AUTOMATIC_PROCESS_ALL:
            lanjut_input = input(f"\n{C.BOLD}{C.YELLOW}Lanjutkan untuk memproses grup/channel dan bot? (y/n): {C.RESET}").lower().strip()
            if lanjut_input != 'y':
                print(f'{C.BOLD}{C.YELLOW}Proses dibatalkan oleh pengguna.{C.RESET}')
                return
        else:
            print(f"\n{C.BOLD}{C.CYAN}Melanjutkan proses secara otomatis...{C.RESET}")

        print(f"\n{C.BOLD}{C.CYAN}Mengumpulkan daftar dialog (chat)... Mohon tunggu.{C.RESET}")
        all_dialogs_api = []
        async for dialog in client.iter_dialogs():
            all_dialogs_api.append(dialog)
        print(f"  {C.BOLD}{C.GREEN}Selesai mengumpulkan {C.BOLD}{len(all_dialogs_api)}{C.GREEN} dialog.{C.RESET}")
        
        groups_channels_to_process_entities = []
        bots_to_process_entities = []
        whitelisted_dialogs_log_ids = set()

        print(f"\n{C.BOLD}{C.CYAN}Memfilter dialog dan menerapkan whitelist...{C.RESET}")
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

            is_whitelisted = False
            if username and username in lower_case_whitelist_usernames:
                is_whitelisted = True
            
            if is_whitelisted:
                if dialog.id not in whitelisted_dialogs_log_ids:
                    print(f"    {C.BOLD}{C.BLUE}↳ [WHITELIST] \"{C.BOLD}{display_title}{C.BLUE}\" akan dilewati.{C.RESET}")
                    whitelisted_dialogs_log_ids.add(dialog.id)
                continue 
            
            if is_bot_flag:
                bots_to_process_entities.append(dialog.entity)
            elif dialog.is_group or dialog.is_channel:
                groups_channels_to_process_entities.append(dialog.entity)

        if whitelisted_dialogs_log_ids:
            print(f"  {C.BOLD}{C.GREEN}Total {C.BOLD}{len(whitelisted_dialogs_log_ids)}{C.GREEN} item terdeteksi dalam whitelist.{C.RESET}")
        else:
            print(f"  {C.BOLD}{C.YELLOW}Tidak ada item dalam dialog yang cocok dengan whitelist.{C.RESET}")

        # --- Fase 1: Keluar dari Grup/Channel ---
        print(f"\n{C.BOLD}{C.MAGENTA}--- FASE 1: KELUAR DARI GRUP/CHANNEL ---{C.RESET}")
        if not groups_channels_to_process_entities:
            print(f"  {C.BOLD}{C.YELLOW}Tidak ada grup/channel untuk diproses.{C.RESET}")
        else:
            print(f"  {C.BOLD}{C.CYAN}Akan memproses {C.BOLD}{len(groups_channels_to_process_entities)}{C.CYAN} grup/channel.{C.RESET}")
            for idx, entity_obj in enumerate(groups_channels_to_process_entities):
                title_to_leave = entity_obj.title if hasattr(entity_obj, 'title') else (f"@{entity_obj.username}" if hasattr(entity_obj, 'username') and entity_obj.username else f"ID:{entity_obj.id}")
                print(f"\n  ({idx+1}/{len(groups_channels_to_process_entities)}) Memproses: \"{C.BOLD}{title_to_leave}{C.RESET}\"")
                
                action_had_flood_wait_group = False
                try:
                    print(f"    {C.BOLD}{C.WHITE}↳ Mencoba meninggalkan...{C.RESET}") # Putih untuk aksi
                    await client.delete_dialog(entity_obj)
                    print(f"    {C.BOLD}{C.GREEN}↳ [BERHASIL] Meninggalkan \"{title_to_leave}\".{C.RESET}")
                except errors.FloodWaitError as e:
                    wait_duration = e.seconds + FLOOD_WAIT_BUFFER
                    print(f"    {C.BOLD}{C.YELLOW}↳ [GAGAL - FLOOD WAIT] Perlu menunggu {e.seconds} dtk.{C.RESET}")
                    print(f"    {C.BOLD}{C.YELLOW}↳ Akan tidur selama {wait_duration} dtk...{C.RESET}")
                    await asyncio.sleep(wait_duration)
                    print(f"    {C.BOLD}{C.YELLOW}↳ Selesai menunggu. Item \"{title_to_leave}\" mungkin belum selesai.{C.RESET}")
                    action_had_flood_wait_group = True
                except Exception as e:
                    print(f"    {C.BOLD}{C.RED}↳ [GAGAL] Meninggalkan \"{title_to_leave}\": {type(e).__name__} - {e}{C.RESET}")
                
                if idx < len(groups_channels_to_process_entities) - 1:
                    delay_msg = f"(Setelah FloodWait) Menunggu {NORMAL_ACTION_DELAY} dtk tambahan..." if action_had_flood_wait_group else f"Menunggu {NORMAL_ACTION_DELAY} dtk..."
                    print(f"    {C.BOLD}{C.YELLOW}↳ {delay_msg}{C.RESET}")
                    await asyncio.sleep(NORMAL_ACTION_DELAY)

        # --- Fase 2: Hapus Obrolan & Blokir Bot ---
        print(f"\n{C.BOLD}{C.MAGENTA}--- FASE 2: HAPUS OBROLAN & BLOKIR BOT ---{C.RESET}")
        if not bots_to_process_entities:
            print(f"  {C.BOLD}{C.YELLOW}Tidak ada bot untuk diproses.{C.RESET}")
        else:
            print(f"  {C.BOLD}{C.CYAN}Akan memproses {C.BOLD}{len(bots_to_process_entities)}{C.CYAN} bot.{C.RESET}")
            for idx, bot_entity in enumerate(bots_to_process_entities):
                bot_name_to_process = bot_entity.first_name if hasattr(bot_entity, 'first_name') and bot_entity.first_name else (f"@{bot_entity.username}" if hasattr(bot_entity, 'username') and bot_entity.username else f"Bot ID:{bot_entity.id}")
                print(f"\n  ({idx+1}/{len(bots_to_process_entities)}) Memproses bot: \"{C.BOLD}{bot_name_to_process}{C.RESET}\"")
                
                action_had_flood_wait_bot = False
                # 1. Blokir Bot
                try:
                    print(f"    {C.BOLD}{C.WHITE}↳ Mencoba memblokir \"{bot_name_to_process}\"...{C.RESET}") # Putih untuk aksi
                    await client(functions.contacts.BlockRequest(id=bot_entity.id))
                    print(f"    {C.BOLD}{C.GREEN}↳ [BERHASIL] Memblokir bot.{C.RESET}")
                except errors.FloodWaitError as e_block_flood:
                    wait_duration = e_block_flood.seconds + FLOOD_WAIT_BUFFER
                    print(f"    {C.BOLD}{C.YELLOW}↳ [GAGAL BLOKIR - FLOOD WAIT] Perlu menunggu {e_block_flood.seconds} dtk.{C.RESET}")
                    print(f"    {C.BOLD}{C.YELLOW}↳ Akan tidur selama {wait_duration} dtk...{C.RESET}")
                    await asyncio.sleep(wait_duration)
                    print(f"    {C.BOLD}{C.YELLOW}↳ Selesai menunggu. Blokir \"{bot_name_to_process}\" mungkin belum berhasil.{C.RESET}")
                    action_had_flood_wait_bot = True
                except errors.UserIsBlockedError:
                    print(f"    {C.BOLD}{C.BLUE}↳ [INFO] Bot \"{bot_name_to_process}\" sudah diblokir.{C.RESET}")
                except Exception as e_block: 
                    print(f"    {C.BOLD}{C.RED}↳ [GAGAL BLOKIR] Gagal memblokir \"{bot_name_to_process}\": {type(e_block).__name__}{C.RESET}")
                
                # 2. Hapus Dialog dengan Bot
                try:
                    print(f"    {C.BOLD}{C.WHITE}↳ Mencoba menghapus obrolan dengan \"{bot_name_to_process}\"...{C.RESET}") # Putih untuk aksi
                    await client.delete_dialog(bot_entity)
                    print(f"    {C.BOLD}{C.GREEN}↳ [BERHASIL] Menghapus obrolan.{C.RESET}")
                except errors.FloodWaitError as e_delete_flood:
                    wait_duration = e_delete_flood.seconds + FLOOD_WAIT_BUFFER
                    print(f"    {C.BOLD}{C.YELLOW}↳ [GAGAL HAPUS - FLOOD WAIT] Perlu menunggu {e_delete_flood.seconds} dtk.{C.RESET}")
                    print(f"    {C.BOLD}{C.YELLOW}↳ Akan tidur selama {wait_duration} dtk...{C.RESET}")
                    await asyncio.sleep(wait_duration)
                    print(f"    {C.BOLD}{C.YELLOW}↳ Selesai menunggu. Hapus dialog \"{bot_name_to_process}\" mungkin belum berhasil.{C.RESET}")
                    action_had_flood_wait_bot = True
                except Exception as e_delete:
                    print(f"    {C.BOLD}{C.RED}↳ [GAGAL HAPUS] Gagal menghapus obrolan \"{bot_name_to_process}\": {type(e_delete).__name__}{C.RESET}")

                if idx < len(bots_to_process_entities) - 1:
                    delay_msg = f"(Setelah FloodWait) Menunggu {NORMAL_ACTION_DELAY} dtk tambahan..." if action_had_flood_wait_bot else f"Menunggu {NORMAL_ACTION_DELAY} dtk..."
                    print(f"    {C.BOLD}{C.YELLOW}↳ {delay_msg}{C.RESET}")
                    await asyncio.sleep(NORMAL_ACTION_DELAY)

        print(f"\n{C.BOLD}{C.GREEN}==============================================={C.RESET}")
        print(f"{C.BOLD}{C.GREEN}=== Semua proses otomatis telah selesai. ==={C.RESET}")
        print(f"{C.BOLD}{C.GREEN}==============================================={C.RESET}")

    except errors.PhoneNumberInvalidError:
        print(f"{C.BOLD}{C.RED}Kesalahan Login: Format nomor telepon tidak valid.{C.RESET}")
    except errors.PhoneCodeInvalidError:
        print(f"{C.BOLD}{C.RED}Kesalahan Login: Kode OTP salah.{C.RESET}")
    except errors.PhoneCodeExpiredError:
        print(f"{C.BOLD}{C.RED}Kesalahan Login: Kode OTP kedaluwarsa.{C.RESET}")
    except errors.SessionPasswordNeededError:
        print(f"{C.BOLD}{C.RED}Kesalahan Login: Kata sandi 2FA salah/diperlukan.{C.RESET}")
    except errors.rpcerrorlist.ApiIdInvalidError:
        print(f"{C.BOLD}{C.RED}Kesalahan Kritis: API_ID atau API_HASH tidak valid.{C.RESET}")
    except ConnectionError:
        print(f"{C.BOLD}{C.RED}Kesalahan Koneksi: Tidak dapat terhubung ke Telegram.{C.RESET}")
    except Exception as e:
        print(f"{C.BOLD}{C.RED}Terjadi kesalahan umum tidak terduga:{C.RESET}")
        print(f"{C.BOLD}{C.RED}  Tipe Error : {type(e).__name__}{C.RESET}")
        print(f"{C.BOLD}{C.RED}  Pesan Error: {e}{C.RESET}")
        print(f"{C.BOLD}{C.YELLOW}Detail Traceback:{C.RESET}")
        traceback.print_exc()
    finally:
        if 'client' in locals() and client.is_connected():
            print(f"\n{C.BOLD}{C.CYAN}Memutus koneksi ke Telegram...{C.RESET}")
            await client.disconnect()
            print(f"  {C.BOLD}{C.GREEN}Koneksi berhasil diputus.{C.RESET}")
        print(f"\n{C.BOLD}{C.MAGENTA}Skrip selesai dijalankan.{C.RESET}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{C.BOLD}{C.YELLOW}Proses dihentikan oleh pengguna (Ctrl+C).{C.RESET}")
    except Exception as e:
        print(f"{C.BOLD}{C.RED}Error tak terduga di luar loop utama: {type(e).__name__} - {e}{C.RESET}")
        traceback.print_exc()
