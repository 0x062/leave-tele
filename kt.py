import asyncio
import os
import time
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession # Meskipun tidak dipakai langsung jika sesi file, impor ini umum
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

async def display_and_select_items(items_to_display, item_type_singular, item_type_plural):
    if not items_to_display:
        print(f'Tidak ada {item_type_plural} yang bisa diproses (setelah filter whitelist).')
        return []

    print(f'\nBerikut adalah {item_type_plural} yang bisa diproses:')
    for i, (display_text, _) in enumerate(items_to_display):
        print(f"{i + 1}. {display_text}")

    print(f'\n--- OPSI UNTUK {item_type_plural.upper()} ---')
    print(f'Masukkan nomor urut {item_type_singular} yang ingin Anda proses, dipisahkan koma (misal: 1,3,5).')
    print(f'Atau ketik "SEMUA" untuk mencoba memproses semua {item_type_plural} yang terdaftar di atas.')
    print(f'Atau ketik "BATAL" untuk melewati bagian ini.')

    choice_str = input(f'Pilihan Anda untuk {item_type_plural}: ').strip().lower()

    if choice_str == 'batal':
        print(f'Pemrosesan {item_type_plural} dibatalkan.')
        return []
    
    selected_entities = []
    if choice_str == 'semua':
        confirm_semua = input(f'PERINGATAN: Anda memilih "SEMUA". Ini akan mencoba memproses {len(items_to_display)} {item_type_plural} yang terdaftar. Apakah Anda yakin? (y/n): ').lower()
        if confirm_semua != 'y':
            print(f'Pemrosesan {item_type_plural} dibatalkan.')
            return []
        for _, dialog_obj in items_to_display:
            selected_entities.append(dialog_obj.entity)
    else:
        try:
            indices = [int(num_str.strip()) - 1 for num_str in choice_str.split(',')]
            for index in indices:
                if 0 <= index < len(items_to_display):
                    selected_entities.append(items_to_display[index][1].entity)
                else:
                    print(f"Nomor urut {index + 1} tidak valid untuk {item_type_plural}, akan diabaikan.")
        except ValueError:
            print(f"Input nomor tidak valid untuk {item_type_plural}. Harap masukkan nomor yang benar atau 'SEMUA'/'BATAL'.")
            return []
            
    return selected_entities

async def main():
    print(f"Memulai skrip Telegram (v8)...")
    lower_case_whitelist_usernames = load_whitelist_usernames()

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

        # Kumpulkan semua dialog dulu
        print('\nMengumpulkan daftar dialog... Mohon tunggu...')
        all_dialogs = []
        async for dialog in client.iter_dialogs():
            all_dialogs.append(dialog)
        
        groups_channels_options_display = []
        bots_options_display = []
        whitelisted_dialogs_log_ids = set()

        print("Memfilter dialog dan menerapkan whitelist...")
        for dialog in all_dialogs:
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
                continue # Lewati item yang di-whitelist

            # Kategorikan item yang tidak di-whitelist
            display_username_str = f"@{username}" if username else "TIDAK ADA"
            if is_bot_flag:
                bot_name = entity.first_name if hasattr(entity, 'first_name') else title
                display_text = f"BOT: \"{bot_name}\" (Username: {display_username_str}, ID: {dialog.id})"
                bots_options_display.append((display_text, dialog))
            elif dialog.is_group or dialog.is_channel:
                display_text = f"\"{title}\" (Tipe: {'Grup' if dialog.is_group else 'Channel'}, Username: {display_username_str}, ID: {dialog.id})"
                groups_channels_options_display.append((display_text, dialog))

        if whitelisted_dialogs_log_ids:
            print(f"\nTotal {len(whitelisted_dialogs_log_ids)} item terdeteksi dalam whitelist dan tidak akan diproses lebih lanjut.")

        # --- Fase 1: Keluar dari Grup/Channel ---
        print("\n--- FASE 1: KELUAR DARI GRUP/CHANNEL ---")
        entities_to_leave = await display_and_select_items(groups_channels_options_display, "grup/channel", "grup/channel")
        
        if entities_to_leave:
            print(f"\nMemulai proses meninggalkan {len(entities_to_leave)} grup/channel yang dipilih...")
            for entity_obj in entities_to_leave:
                title_to_leave = entity_obj.title if hasattr(entity_obj, 'title') else (f"@{entity_obj.username}" if hasattr(entity_obj, 'username') else "N/A")
                print(f"Mencoba meninggalkan: \"{title_to_leave}\"...")
                try:
                    await client.delete_dialog(entity_obj) # Meninggalkan dan menghapus dari daftar
                    print(f"  Berhasil meninggalkan: \"{title_to_leave}\"")
                except Exception as e:
                    print(f"  Gagal meninggalkan \"{title_to_leave}\": {type(e).__name__} - {e}")
                await asyncio.sleep(2)

        # --- Fase 2: Hapus Obrolan Bot ---
        print("\n--- FASE 2: HAPUS OBROLAN DENGAN BOT ---")
        bots_to_delete = await display_and_select_items(bots_options_display, "bot", "bot")

        if bots_to_delete:
            print(f"\nMemulai proses memblokir dan menghapus obrolan dengan {len(bots_to_delete)} bot yang dipilih...")
            for bot_entity in bots_to_delete:
                bot_name_to_delete = bot_entity.first_name if hasattr(bot_entity, 'first_name') else (f"@{bot_entity.username}" if hasattr(bot_entity, 'username') else "Bot Tanpa Nama")
                print(f"Memproses bot: \"{bot_name_to_delete}\"...")
                try:
                    # 1. Blokir bot
                    print(f"  Mencoba memblokir \"{bot_name_to_delete}\"...")
                    await client(functions.contacts.BlockRequest(id=bot_entity.id))
                    print(f"    Berhasil memblokir.")
                    
                    # 2. Hapus dialog (obrolan)
                    print(f"  Mencoba menghapus obrolan dengan \"{bot_name_to_delete}\"...")
                    await client.delete_dialog(bot_entity)
                    print(f"    Berhasil menghapus obrolan.")
                except errors.UserIsBlockedError:
                     print(f"  Info: \"{bot_name_to_delete}\" sudah diblokir sebelumnya. Menghapus obrolan...")
                     try:
                         await client.delete_dialog(bot_entity)
                         print(f"    Berhasil menghapus obrolan yang sudah diblokir.")
                     except Exception as e_del:
                         print(f"    Gagal menghapus obrolan (setelah blokir): {type(e_del).__name__} - {e_del}")
                except Exception as e:
                    print(f"  Gagal memproses bot \"{bot_name_to_delete}\": {type(e).__name__} - {e}")
                await asyncio.sleep(2) # Jeda

        print('\nSemua proses yang dipilih telah selesai.')

    except errors.PhoneNumberInvalidError:
        print("Kesalahan: Format nomor telepon tidak valid.")
    except errors.PhoneCodeInvalidError:
        print("Kesalahan: Kode verifikasi yang Anda masukkan salah.")
    except errors.PhoneCodeExpiredError:
        print("Kesalahan: Kode verifikasi sudah kedaluwarsa. Silakan coba lagi.")
    except errors.SessionPasswordNeededError:
         print("Kesalahan: Kata sandi Two-Factor Authentication (2FA) diperlukan atau salah.")
    except Exception as e:
        print(f"Terjadi kesalahan umum yang tidak terduga: {type(e).__name__} - {e}")
    finally:
        if client.is_connected():
            print("Memutus koneksi ke Telegram...")
            await client.disconnect()
        print("Skrip selesai.")

if __name__ == '__main__':
    asyncio.run(main())
