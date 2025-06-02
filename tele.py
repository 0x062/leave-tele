import asyncio
import os
from telethon import TelegramClient, errors, functions, types
from dotenv import load_dotenv
import traceback
from colorama import Fore, Style, init as colorama_init

# Inisialisasi Colorama
# autoreset=True akan otomatis menambahkan Style.RESET_ALL setelah setiap print berwarna
colorama_init(autoreset=True)

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
        # Penggunaan Colorama: Style.BRIGHT untuk tebal, Fore untuk warna
        print(f"{Style.BRIGHT}{Fore.RED}Kesalahan Kritis: TELEGRAM_API_ID atau TELEGRAM_API_HASH tidak ditemukan di file .env.")
        print(f"{Fore.RED}Pastikan file .env ada dan berisi variabel tersebut.")
        print(f"{Fore.RED}Contoh .env:\nTELEGRAM_API_ID=1234567\nTELEGRAM_API_HASH=abcdef1234567890abcdef1234567890")
        exit(1)
    try:
        api_id = int(API_ID_STR)
        return api_id, API_HASH
    except ValueError:
        print(f"{Style.BRIGHT}{Fore.RED}Kesalahan Kritis: TELEGRAM_API_ID ('{API_ID_STR}') harus berupa angka integer.")
        exit(1)

API_ID, API_HASH = initialize_env_vars()

SESSION_FILE_NAME = 'my_telegram_session.session'
WHITELIST_FILE_PATH = 'whitelist.txt'

def load_whitelist_usernames():
    usernames = []
    # Style.NORMAL mungkin diperlukan jika baris sebelumnya menggunakan Style.BRIGHT dan autoreset tidak cukup
    print(f"\n{Style.BRIGHT}{Fore.CYAN}Membaca file whitelist: {Style.BRIGHT}{Fore.WHITE}{WHITELIST_FILE_PATH}")
    try:
        if os.path.exists(WHITELIST_FILE_PATH):
            with open(WHITELIST_FILE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    username = line.strip().lower()
                    if username and not username.startswith('#'):
                        usernames.append(username)
            if usernames:
                print(f"  {Style.BRIGHT}{Fore.GREEN}Berhasil memuat {Style.BRIGHT}{Fore.WHITE}{len(usernames)}{Style.BRIGHT}{Fore.GREEN} username dari whitelist.")
            else:
                print(f"  {Style.BRIGHT}{Fore.YELLOW}File whitelist ditemukan namun kosong atau hanya berisi komentar.")
        else:
            print(f"  {Style.BRIGHT}{Fore.YELLOW}Peringatan: File whitelist '{WHITELIST_FILE_PATH}' tidak ditemukan.")
    except Exception as e:
        print(f"  {Style.BRIGHT}{Fore.RED}Error saat memuat whitelist: {e}")
    return usernames

async def main():
    print(f"{Style.BRIGHT}{Fore.MAGENTA}===============================================")
    print(f"{Style.BRIGHT}{Fore.MAGENTA}=== SKRIP MANAJEMEN AKUN TELEGRAM v14 (Colorama) ===")
    print(f"{Style.BRIGHT}{Fore.MAGENTA}===============================================")
    
    if AUTOMATIC_PROCESS_ALL:
        print(f"\n{Style.BRIGHT}{Fore.CYAN}[MODE OTOMATIS AKTIF]{Style.RESET_ALL} {Style.BRIGHT}{Fore.YELLOW}Skrip akan memproses semua item non-whitelist tanpa konfirmasi.")
    else:
        print(f"\n{Style.BRIGHT}{Fore.CYAN}[MODE MANUAL AKTIF]{Style.RESET_ALL} {Style.BRIGHT}{Fore.YELLOW}Skrip akan meminta konfirmasi sebelum memproses.")

    lower_case_whitelist_usernames = load_whitelist_usernames()

    client = TelegramClient(SESSION_FILE_NAME, API_ID, API_HASH, retry_delay=10, connection_retries=5)

    print(f"\n{Style.BRIGHT}{Fore.CYAN}Menghubungkan ke Telegram...")
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print(f"  {Style.BRIGHT}{Fore.YELLOW}Sesi tidak terotorisasi. Memulai proses login interaktif...")
            phone_number = input(f"  {Style.BRIGHT}{Fore.WHITE}Masukkan nomor telepon Anda (format +62xxxx): {Style.RESET_ALL}").strip() # Reset setelah input
            await client.send_code_request(phone_number)
            try:
                code = input(f"  {Style.BRIGHT}{Fore.WHITE}Masukkan kode OTP yang Anda terima: {Style.RESET_ALL}").strip()
                await client.sign_in(phone_number, code)
            except errors.SessionPasswordNeededError:
                password = input(f"  {Style.BRIGHT}{Fore.WHITE}Masukkan kata sandi Two-Factor Authentication (2FA): {Style.RESET_ALL}").strip()
                await client.sign_in(password=password)
            print(f"  {Style.BRIGHT}{Fore.GREEN}Login berhasil! Sesi disimpan di {Style.BRIGHT}{Fore.WHITE}{SESSION_FILE_NAME}")
        
        me = await client.get_me()
        # Menggabungkan Style.BRIGHT dengan Fore.LIGHT<COLOR>_EX (jika ada) atau Fore.<COLOR>
        # Colorama LIGHT..._EX adalah yang paling mendekati \033[9xm
        print(f"\n{Style.BRIGHT}{Fore.LIGHTGREEN_EX}Berhasil terhubung sebagai: {Style.BRIGHT}{Fore.WHITE}{me.first_name or ''} {me.last_name or ''}{Style.RESET_ALL} {Style.BRIGHT}{Fore.LIGHTGREEN_EX}(@{me.username if me.username else 'Tanpa Username'})")
        print(f"{Style.BRIGHT}{Fore.LIGHTBLUE_EX}-----------------------------------------------")

        if not AUTOMATIC_PROCESS_ALL:
            lanjut_input = input(f"\n{Style.BRIGHT}{Fore.YELLOW}Lanjutkan untuk memproses grup/channel dan bot? (y/n): {Style.RESET_ALL}").lower().strip()
            if lanjut_input != 'y':
                print(f'{Style.BRIGHT}{Fore.YELLOW}Proses dibatalkan oleh pengguna.')
                return
        else:
            print(f"\n{Style.BRIGHT}{Fore.CYAN}Melanjutkan proses secara otomatis...")

        print(f"\n{Style.BRIGHT}{Fore.CYAN}Mengumpulkan daftar dialog (chat)... Mohon tunggu.")
        all_dialogs_api = []
        async for dialog in client.iter_dialogs():
            all_dialogs_api.append(dialog)
        print(f"  {Style.BRIGHT}{Fore.LIGHTGREEN_EX}Selesai mengumpulkan {Style.BRIGHT}{Fore.WHITE}{len(all_dialogs_api)}{Style.BRIGHT}{Fore.LIGHTGREEN_EX} dialog.")
        
        groups_channels_to_process_entities = []
        bots_to_process_entities = []
        whitelisted_dialogs_log_ids = set()

        print(f"\n{Style.BRIGHT}{Fore.CYAN}Memfilter dialog dan menerapkan whitelist...")
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
                    print(f"    {Style.BRIGHT}{Fore.LIGHTBLUE_EX}↳ [WHITELIST] \"{Style.BRIGHT}{Fore.WHITE}{display_title}{Style.BRIGHT}{Fore.LIGHTBLUE_EX}\" akan dilewati.")
                    whitelisted_dialogs_log_ids.add(dialog.id)
                continue 
            
            if is_bot_flag:
                bots_to_process_entities.append(dialog.entity)
            elif dialog.is_group or dialog.is_channel:
                groups_channels_to_process_entities.append(dialog.entity)

        if whitelisted_dialogs_log_ids:
            print(f"  {Style.BRIGHT}{Fore.LIGHTGREEN_EX}Total {Style.BRIGHT}{Fore.WHITE}{len(whitelisted_dialogs_log_ids)}{Style.BRIGHT}{Fore.LIGHTGREEN_EX} item terdeteksi dalam whitelist.")
        else:
            print(f"  {Style.BRIGHT}{Fore.YELLOW}Tidak ada item dalam dialog yang cocok dengan whitelist.")

        # --- Fase 1: Keluar dari Grup/Channel ---
        print(f"\n{Style.BRIGHT}{Fore.MAGENTA}--- FASE 1: KELUAR DARI GRUP/CHANNEL ---")
        if not groups_channels_to_process_entities:
            print(f"  {Style.BRIGHT}{Fore.YELLOW}Tidak ada grup/channel untuk diproses.")
        else:
            print(f"  {Style.BRIGHT}{Fore.CYAN}Akan memproses {Style.BRIGHT}{Fore.WHITE}{len(groups_channels_to_process_entities)}{Style.BRIGHT}{Fore.CYAN} grup/channel.")
            for idx, entity_obj in enumerate(groups_channels_to_process_entities):
                title_to_leave = entity_obj.title if hasattr(entity_obj, 'title') else (f"@{entity_obj.username}" if hasattr(entity_obj, 'username') and entity_obj.username else f"ID:{entity_obj.id}")
                print(f"\n  ({idx+1}/{len(groups_channels_to_process_entities)}) Memproses: \"{Style.BRIGHT}{Fore.WHITE}{title_to_leave}{Style.RESET_ALL}\"") # Judul item
                
                action_had_flood_wait_group = False
                try:
                    print(f"    {Fore.WHITE}↳ Mencoba meninggalkan...") # Aksi: Putih biasa (agar tidak terlalu ramai)
                    await client.delete_dialog(entity_obj)
                    print(f"    {Style.BRIGHT}{Fore.LIGHTGREEN_EX}↳ [BERHASIL] Meninggalkan \"{title_to_leave}\".")
                except errors.FloodWaitError as e:
                    wait_duration = e.seconds + FLOOD_WAIT_BUFFER
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ [GAGAL - FLOOD WAIT] Perlu menunggu {e.seconds} dtk.")
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ Akan tidur selama {wait_duration} dtk...")
                    await asyncio.sleep(wait_duration)
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ Selesai menunggu. Item \"{title_to_leave}\" mungkin belum selesai.")
                    action_had_flood_wait_group = True
                except Exception as e:
                    print(f"    {Style.BRIGHT}{Fore.RED}↳ [GAGAL] Meninggalkan \"{title_to_leave}\": {type(e).__name__} - {e}")
                
                if idx < len(groups_channels_to_process_entities) - 1:
                    delay_msg = f"(Setelah FloodWait) Menunggu {NORMAL_ACTION_DELAY} dtk tambahan..." if action_had_flood_wait_group else f"Menunggu {NORMAL_ACTION_DELAY} dtk..."
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ {delay_msg}")
                    await asyncio.sleep(NORMAL_ACTION_DELAY)

        # --- Fase 2: Hapus Obrolan & Blokir Bot ---
        print(f"\n{Style.BRIGHT}{Fore.MAGENTA}--- FASE 2: HAPUS OBROLAN & BLOKIR BOT ---")
        if not bots_to_process_entities:
            print(f"  {Style.BRIGHT}{Fore.YELLOW}Tidak ada bot untuk diproses.")
        else:
            print(f"  {Style.BRIGHT}{Fore.CYAN}Akan memproses {Style.BRIGHT}{Fore.WHITE}{len(bots_to_process_entities)}{Style.BRIGHT}{Fore.CYAN} bot.")
            for idx, bot_entity in enumerate(bots_to_process_entities):
                bot_name_to_process = bot_entity.first_name if hasattr(bot_entity, 'first_name') and bot_entity.first_name else (f"@{bot_entity.username}" if hasattr(bot_entity, 'username') and bot_entity.username else f"Bot ID:{bot_entity.id}")
                print(f"\n  ({idx+1}/{len(bots_to_process_entities)}) Memproses bot: \"{Style.BRIGHT}{Fore.WHITE}{bot_name_to_process}{Style.RESET_ALL}\"")
                
                action_had_flood_wait_bot = False
                try:
                    print(f"    {Fore.WHITE}↳ Mencoba memblokir \"{bot_name_to_process}\"...")
                    await client(functions.contacts.BlockRequest(id=bot_entity.id))
                    print(f"    {Style.BRIGHT}{Fore.LIGHTGREEN_EX}↳ [BERHASIL] Memblokir bot.")
                except errors.FloodWaitError as e_block_flood:
                    wait_duration = e_block_flood.seconds + FLOOD_WAIT_BUFFER
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ [GAGAL BLOKIR - FLOOD WAIT] Perlu menunggu {e_block_flood.seconds} dtk.")
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ Akan tidur selama {wait_duration} dtk...")
                    await asyncio.sleep(wait_duration)
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ Selesai menunggu. Blokir \"{bot_name_to_process}\" mungkin belum berhasil.")
                    action_had_flood_wait_bot = True
                except errors.UserIsBlockedError:
                    print(f"    {Style.BRIGHT}{Fore.LIGHTBLUE_EX}↳ [INFO] Bot \"{bot_name_to_process}\" sudah diblokir.")
                except Exception as e_block: 
                    print(f"    {Style.BRIGHT}{Fore.RED}↳ [GAGAL BLOKIR] Gagal memblokir \"{bot_name_to_process}\": {type(e_block).__name__}")
                
                try:
                    print(f"    {Fore.WHITE}↳ Mencoba menghapus obrolan dengan \"{bot_name_to_process}\"...")
                    await client.delete_dialog(bot_entity)
                    print(f"    {Style.BRIGHT}{Fore.LIGHTGREEN_EX}↳ [BERHASIL] Menghapus obrolan.")
                except errors.FloodWaitError as e_delete_flood:
                    wait_duration = e_delete_flood.seconds + FLOOD_WAIT_BUFFER
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ [GAGAL HAPUS - FLOOD WAIT] Perlu menunggu {e_delete_flood.seconds} dtk.")
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ Akan tidur selama {wait_duration} dtk...")
                    await asyncio.sleep(wait_duration)
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ Selesai menunggu. Hapus dialog \"{bot_name_to_process}\" mungkin belum berhasil.")
                    action_had_flood_wait_bot = True
                except Exception as e_delete:
                    print(f"    {Style.BRIGHT}{Fore.RED}↳ [GAGAL HAPUS] Gagal menghapus obrolan \"{bot_name_to_process}\": {type(e_delete).__name__}")

                if idx < len(bots_to_process_entities) - 1:
                    delay_msg = f"(Setelah FloodWait) Menunggu {NORMAL_ACTION_DELAY} dtk tambahan..." if action_had_flood_wait_bot else f"Menunggu {NORMAL_ACTION_DELAY} dtk..."
                    print(f"    {Style.BRIGHT}{Fore.YELLOW}↳ {delay_msg}")
                    await asyncio.sleep(NORMAL_ACTION_DELAY)

        print(f"\n{Style.BRIGHT}{Fore.LIGHTGREEN_EX}===============================================")
        print(f"{Style.BRIGHT}{Fore.LIGHTGREEN_EX}=== Semua proses otomatis telah selesai. ===")
        print(f"{Style.BRIGHT}{Fore.LIGHTGREEN_EX}===============================================")

    except errors.PhoneNumberInvalidError:
        print(f"{Style.BRIGHT}{Fore.RED}Kesalahan Login: Format nomor telepon tidak valid.")
    except errors.PhoneCodeInvalidError:
        print(f"{Style.BRIGHT}{Fore.RED}Kesalahan Login: Kode OTP salah.")
    except errors.PhoneCodeExpiredError:
        print(f"{Style.BRIGHT}{Fore.RED}Kesalahan Login: Kode OTP kedaluwarsa.")
    except errors.SessionPasswordNeededError:
        print(f"{Style.BRIGHT}{Fore.RED}Kesalahan Login: Kata sandi 2FA salah/diperlukan.")
    except errors.rpcerrorlist.ApiIdInvalidError:
        print(f"{Style.BRIGHT}{Fore.RED}Kesalahan Kritis: API_ID atau API_HASH tidak valid.")
    except ConnectionError:
        print(f"{Style.BRIGHT}{Fore.RED}Kesalahan Koneksi: Tidak dapat terhubung ke Telegram.")
    except Exception as e:
        print(f"{Style.BRIGHT}{Fore.RED}Terjadi kesalahan umum tidak terduga:")
        print(f"{Style.BRIGHT}{Fore.RED}  Tipe Error : {type(e).__name__}")
        print(f"{Style.BRIGHT}{Fore.RED}  Pesan Error: {e}")
        print(f"{Style.BRIGHT}{Fore.YELLOW}Detail Traceback:")
        traceback.print_exc() # Ini akan mencetak dengan warna default terminal untuk traceback
    finally:
        if 'client' in locals() and client.is_connected():
            print(f"\n{Style.BRIGHT}{Fore.CYAN}Memutus koneksi ke Telegram...")
            await client.disconnect()
            print(f"  {Style.BRIGHT}{Fore.LIGHTGREEN_EX}Koneksi berhasil diputus.")
        print(f"\n{Style.BRIGHT}{Fore.MAGENTA}Skrip selesai dijalankan.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Style.BRIGHT}{Fore.YELLOW}Proses dihentikan oleh pengguna (Ctrl+C).")
    except Exception as e:
        print(f"{Style.BRIGHT}{Fore.RED}Error tak terduga di luar loop utama: {type(e).__name__} - {e}")
        traceback.print_exc()
