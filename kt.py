import asyncio
import os
import time
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession
from dotenv import load_dotenv

# Muat variabel dari .env
load_dotenv()

API_ID_STR = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

if not API_ID_STR or not API_HASH:
    print("Kesalahan: TELEGRAM_API_ID atau TELEGRAM_API_HASH tidak ditemukan di file .env.")
    print("Pastikan file .env sudah benar dan berisi variabel tersebut.")
    exit(1)

try:
    API_ID = int(API_ID_STR)
except ValueError:
    print(f"Kesalahan: TELEGRAM_API_ID ('{API_ID_STR}') harus berupa angka.")
    exit(1)

SESSION_FILE_NAME = 'my_telegram_session.session' # Nama file sesi Telethon
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
    print(f"Menggunakan Telethon untuk keluar dari grup/channel Telegram...")
    lower_case_whitelist_usernames = load_whitelist_usernames()

    # Membuat atau memuat sesi dari file
    client = TelegramClient(SESSION_FILE_NAME, API_ID, API_HASH)

    print("Mencoba menghubungkan ke Telegram...")
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Sesi tidak terotorisasi. Memulai proses login...")
            phone_number = input('Masukkan nomor telepon Anda (format +62xxxx): ')
            await client.send_code_request(phone_number)
            try:
                await client.sign_in(phone_number, input('Masukkan kode yang Anda terima: '))
            except errors.SessionPasswordNeededError:
                await client.sign_in(password=input('Masukkan kata sandi Two-Factor Authentication (2FA) Anda: '))
        
        me = await client.get_me()
        print(f"\nBerhasil terhubung sebagai: {me.first_name} (@{me.username if me.username else 'Tanpa Username'})")
        print("---\n")

        lanjut = input('Lanjutkan untuk mendapatkan daftar grup/channel dan memilih mana yang akan ditinggalkan? (y/n): ').lower()
        if lanjut != 'y':
            print('Proses dibatalkan oleh pengguna.')
            return

        print('\nMendapatkan daftar dialog (grup dan channel)... Mohon tunggu...')
        dialogs_to_process = []
        leaveable_dialogs_display = [] # Untuk ditampilkan ke pengguna
        whitelisted_dialogs_log_ids = set()

        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                entity = dialog.entity
                title = dialog.title
                username = None
                if hasattr(entity, 'username') and entity.username:
                    username = entity.username.lower()

                is_whitelisted = False
                if username and username in lower_case_whitelist_usernames:
                    is_whitelisted = True
                
                if is_whitelisted:
                    if dialog.id not in whitelisted_dialogs_log_ids:
                        print(f"   -> \"{title}\" (@{username if username else 'N/A'}) ada di WHITELIST, akan dilewati.")
                        whitelisted_dialogs_log_ids.add(dialog.id)
                else:
                    dialogs_to_process.append(dialog)
                    display_username = f"@{username}" if username else "TIDAK ADA"
                    leaveable_dialogs_display.append(
                        (f"{len(leaveable_dialogs_display) + 1}. \"{title}\" (ID: {dialog.id}, Username: {display_username})", dialog)
                    )
        
        if whitelisted_dialogs_log_ids:
            print(f"\nTotal {len(whitelisted_dialogs_log_ids)} item terdeteksi dalam whitelist dan tidak akan ditawarkan untuk ditinggalkan.")

        if not leaveable_dialogs_display:
            print('Tidak ada grup atau channel yang bisa ditinggalkan (setelah filter whitelist).')
            return

        print('\nBerikut adalah grup dan channel yang bisa ditinggalkan:')
        for display_text, _ in leaveable_dialogs_display:
            print(display_text)

        print('\n--- PENTING ---')
        print('Masukkan nomor urut grup/channel yang ingin Anda tinggalkan, dipisahkan koma (misal: 1,3,5).')
        print('Atau ketik "SEMUA" untuk mencoba meninggalkan semua yang terdaftar di atas.')
        print('Atau ketik "BATAL" untuk keluar.')

        choice_str = input('Pilihan Anda: ').strip().lower()

        if choice_str == 'batal':
            print('Proses dibatalkan.')
            return

        dialogs_to_leave_entities = []
        if choice_str == 'semua':
            confirm_semua = input(f'PERINGATAN: Anda memilih "SEMUA". Ini akan mencoba meninggalkan {len(leaveable_dialogs_display)} grup/channel yang terdaftar. Apakah Anda yakin? (y/n): ').lower()
            if confirm_semua != 'y':
                print('Proses dibatalkan.')
                return
            for _, dialog_obj in leaveable_dialogs_display:
                dialogs_to_leave_entities.append(dialog_obj.entity)
        else:
            try:
                indices = [int(num_str.strip()) - 1 for num_str in choice_str.split(',')]
                for index in indices:
                    if 0 <= index < len(leaveable_dialogs_display):
                        dialogs_to_leave_entities.append(leaveable_dialogs_display[index][1].entity)
                    else:
                        print(f"Nomor urut {index + 1} tidak valid, akan diabaikan.")
            except ValueError:
                print("Input nomor tidak valid. Harap masukkan nomor yang benar atau 'SEMUA'/'BATAL'.")
                return
        
        if not dialogs_to_leave_entities:
            print('Tidak ada grup/channel yang dipilih untuk ditinggalkan.')
            return

        print(f"\nMemulai proses meninggalkan {len(dialogs_to_leave_entities)} grup/channel yang dipilih...")
        for entity_to_leave in dialogs_to_leave_entities:
            title_to_leave = "N/A"
            if hasattr(entity_to_leave, 'title'):
                title_to_leave = entity_to_leave.title
            elif hasattr(entity_to_leave, 'username'): # Untuk user/bot tanpa title eksplisit di entity
                 title_to_leave = f"@{entity_to_leave.username}"

            print(f"Mencoba meninggalkan: \"{title_to_leave}\"...")
            try:
                # client.delete_dialog() akan meninggalkan dan menghapus dari daftar chat
                await client.delete_dialog(entity_to_leave)
                print(f"  Berhasil meninggalkan: \"{title_to_leave}\"")
            except errors.UserIsBlockedError:
                 print(f"  Tidak bisa meninggalkan \"{title_to_leave}\", mungkin Anda diblokir atau chat tidak ada lagi.")
            except errors.ChannelPrivateError:
                 print(f"  Tidak bisa meninggalkan \"{title_to_leave}\", channel bersifat privat atau Anda tidak memiliki akses.")
            except errors.ChatAdminRequiredError:
                 print(f"  Tidak bisa meninggalkan \"{title_to_leave}\", Anda adalah admin. Turunkan status admin Anda atau transfer kepemilikan.")
            except Exception as e:
                print(f"  Gagal meninggalkan \"{title_to_leave}\": {type(e).__name__} - {e}")
            
            await asyncio.sleep(2.5) # Jeda antar operasi untuk menghindari pembatasan API

        print('\nProses meninggalkan grup/channel selesai.')

    except errors.PhoneNumberInvalidError:
        print("Kesalahan: Format nomor telepon tidak valid. Pastikan menggunakan format internasional (misal: +628123456789).")
    except errors.PhoneCodeInvalidError:
        print("Kesalahan: Kode verifikasi yang Anda masukkan salah.")
    except errors.PhoneCodeExpiredError:
        print("Kesalahan: Kode verifikasi sudah kedaluwarsa. Silakan coba lagi.")
    except Exception as e:
        print(f"Terjadi kesalahan umum: {type(e).__name__} - {e}")
    finally:
        if client.is_connected():
            print("Memutus koneksi ke Telegram...")
            await client.disconnect()
        print("Skrip selesai.")

if __name__ == '__main__':
    asyncio.run(main())
