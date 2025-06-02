// lv.js - Versi 7 (Menggunakan paket 'telegram' untuk GramJS)
require('dotenv').config();

// Menggunakan 'telegram' untuk GramJS
const { TelegramClient, Api, sessions } = require('telegram');
const input = require('input');
const fs = require('node:fs');
const path = require('node:path');

// Hapus blok debugging karena kita sudah tahu masalahnya ada di nama paket

const apiId = parseInt(process.env.TELEGRAM_API_ID);
const apiHash = process.env.TELEGRAM_API_HASH;

if (isNaN(apiId) || !apiHash) {
    console.error("Kesalahan: TELEGRAM_API_ID atau TELEGRAM_API_HASH tidak valid atau tidak ditemukan di file .env.");
    process.exit(1);
}

const SESSION_FILE_PATH = path.join(__dirname, 'session.txt');
const WHITELIST_FILE_PATH = path.join(__dirname, 'whitelist.txt');

function loadSession() {
  try {
    if (fs.existsSync(SESSION_FILE_PATH)) {
      console.log(`Memuat sesi dari ${SESSION_FILE_PATH}...`);
      return fs.readFileSync(SESSION_FILE_PATH, 'utf8');
    }
  } catch (error) {
    console.warn("Peringatan: Tidak dapat memuat file sesi:", error.message);
  }
  return '';
}

function saveSession(sessionString) {
  try {
    fs.writeFileSync(SESSION_FILE_PATH, sessionString, 'utf8');
    console.log(`Sesi berhasil disimpan ke ${SESSION_FILE_PATH}`);
  } catch (error) {
    console.error("Kesalahan: Gagal menyimpan file sesi:", error.message);
  }
}

function loadWhitelistUsernames() {
  const usernames = [];
  try {
    if (fs.existsSync(WHITELIST_FILE_PATH)) {
      console.log(`Memuat whitelist usernames dari ${WHITELIST_FILE_PATH}...`);
      const fileContent = fs.readFileSync(WHITELIST_FILE_PATH, 'utf8');
      fileContent
        .split(/\r?\n/)
        .forEach(line => {
          const username = line.trim().toLowerCase();
          if (username.length > 0) {
            usernames.push(username);
          }
        });
      if (usernames.length > 0) {
        console.log(`${usernames.length} username berhasil dimuat dari whitelist.`);
      } else {
        console.log(`File whitelist '${WHITELIST_FILE_PATH}' ditemukan, tetapi kosong atau tidak mengandung username yang valid.`);
      }
    } else {
      console.warn(`Peringatan: File whitelist '${WHITELIST_FILE_PATH}' tidak ditemukan. Tidak ada username yang di-whitelist.`);
    }
  } catch (error) {
    console.warn(`Peringatan: Gagal memuat whitelist dari '${WHITELIST_FILE_PATH}': ${error.message}`);
  }
  return usernames;
}


async function main() {
    let stringSessionValue = loadSession();
    const lowerCaseWhitelistUsernames = loadWhitelistUsernames();

    // Menggunakan sessions.StringSession dari paket 'telegram'
    const stringSession = new sessions.StringSession(stringSessionValue);

    console.log('Memuat skrip untuk keluar dari grup/channel Telegram (v7)...');
    // Menggunakan TelegramClient dari paket 'telegram'
    const client = new TelegramClient(stringSession, apiId, apiHash, {
        connectionRetries: 5,
    });

    try {
        await client.start({
            phoneNumber: async () => {
                if (stringSessionValue) return '';
                return await input.text('Masukkan nomor telepon Anda (format +62xxxx): ');
            },
            password: async () => await input.text('Masukkan kata sandi Telegram Anda (jika ada, tekan Enter jika tidak ada): '),
            phoneCode: async () => {
                if (stringSessionValue && client.connected && !await client.isUserAuthorized()) {
                } else if (stringSessionValue && client.connected) {
                    return '';
                }
                return await input.text('Masukkan kode yang Anda terima di Telegram: ');
            },
            onError: (err) => console.error('Kesalahan saat login:', err.message),
        });

        console.log('\nAnda berhasil terhubung ke Telegram.');
        const currentSession = client.session.save();
        if (currentSession && currentSession !== stringSessionValue) {
            saveSession(currentSession);
        }
        console.log('---\n');

        if (!await input.confirm('Lanjutkan untuk mendapatkan daftar grup/channel dan memilih mana yang akan ditinggalkan? (y/n)')) {
            console.log('Proses dibatalkan oleh pengguna.');
            return;
        }

        console.log('\nMendapatkan daftar dialog (grup dan channel)... Mohon tunggu...');
        const dialogs = await client.getDialogs({});
        const leaveableDialogs = [];
        const whitelistedDialogsLog = new Set();

        console.log('\nBerikut adalah grup dan channel Anda (item dalam whitelist akan ditandai dan dilewati):');

        for (const dialog of dialogs) {
            if ((dialog.isGroup || dialog.isChannel) && dialog.entity && dialog.title) {
                let isWhitelisted = false;
                const dialogUsernameLower = dialog.entity.username ? dialog.entity.username.toLowerCase() : null;

                if (dialogUsernameLower && lowerCaseWhitelistUsernames.includes(dialogUsernameLower)) {
                    isWhitelisted = true;
                }

                if (isWhitelisted) {
                    if (!whitelistedDialogsLog.has(dialog.id.toString())) {
                        console.log(`   -> "${dialog.title}" (@${dialogUsernameLower}) ada di WHITELIST (dari file), akan dilewati.`);
                        whitelistedDialogsLog.add(dialog.id.toString());
                    }
                } else {
                    console.log(`${leaveableDialogs.length + 1}. ${dialog.title} (ID: ${dialog.id}, Username: ${dialog.entity.username ? '@'+dialog.entity.username : 'TIDAK ADA'})`);
                    leaveableDialogs.push(dialog);
                }
            }
        }
        
        if (whitelistedDialogsLog.size > 0) {
            console.log(`\nTotal ${whitelistedDialogsLog.size} item terdeteksi dalam whitelist username dan tidak akan ditawarkan untuk ditinggalkan.`);
        }

        if (leaveableDialogs.length === 0) {
            console.log('Tidak ada grup atau channel yang bisa ditinggalkan (setelah filter whitelist atau tidak ada yang memenuhi kriteria).');
            return;
        }

        console.log('\n--- PENTING ---');
        // ... (sisa kode fungsi main tetap sama) ...
        console.log('Masukkan nomor urut grup/channel yang ingin Anda tinggalkan dari daftar di atas, dipisahkan koma (misal: 1,3,5).');
        console.log('Atau ketik "SEMUA" untuk mencoba meninggalkan semua yang terdaftar (yang tidak di-whitelist).');
        console.log('Atau ketik "BATAL" untuk keluar dari skrip.');

        const choice = await input.text('Pilihan Anda: ');

        if (choice.toLowerCase() === 'batal') {
            console.log('Proses dibatalkan.');
            return;
        }

        let dialogsToLeave = [];
        if (choice.toLowerCase() === 'semua') {
            if (!await input.confirm(`PERINGATAN: Anda memilih "SEMUA". Ini akan mencoba meninggalkan ${leaveableDialogs.length} grup/channel yang terdaftar. Apakah Anda yakin? (y/n)`)) {
                console.log('Proses dibatalkan.');
                return;
            }
            dialogsToLeave = leaveableDialogs;
        } else {
            const indices = choice.split(',').map(numStr => parseInt(numStr.trim(), 10) - 1);
            indices.forEach(index => {
                if (index >= 0 && index < leaveableDialogs.length) {
                    dialogsToLeave.push(leaveableDialogs[index]);
                } else {
                    console.warn(`Nomor urut ${index + 1} tidak valid atau di luar jangkauan, akan diabaikan.`);
                }
            });
        }

        if (dialogsToLeave.length === 0) {
            console.log('Tidak ada grup/channel yang dipilih untuk ditinggalkan.');
            return;
        }

        console.log(`\nMemulai proses meninggalkan ${dialogsToLeave.length} grup/channel yang dipilih...`);
        for (const dialog of dialogsToLeave) {
            const dialogUsernameLower = dialog.entity.username ? dialog.entity.username.toLowerCase() : null;
            if (dialogUsernameLower && lowerCaseWhitelistUsernames.includes(dialogUsernameLower)) {
                 console.log(`   INFO: Melewati "${dialog.title}" (@${dialogUsernameLower}) karena terdeteksi di whitelist (pengaman).`);
                continue;
            }

            try {
                console.log(`Mencoba meninggalkan: "${dialog.title}" (Username: ${dialog.entity.username ? '@'+dialog.entity.username : 'TIDAK ADA'}) ...`);
                // Menggunakan Api dari paket 'telegram'
                if (dialog.isChannel || (dialog.isGroup && dialog.entity?.className === 'Channel')) {
                    await client.invoke( new Api.channels.LeaveChannel({ channel: dialog.entity }) );
                    console.log(`  Berhasil meninggalkan channel/supergroup: "${dialog.title}"`);
                } else if (dialog.isGroup && dialog.entity?.className === 'Chat') {
                    await client.invoke(new Api.messages.DeleteChatUser({ chatId: dialog.entity.id, userId: await client.getMe() }));
                    console.log(`  Berhasil meninggalkan grup dasar: "${dialog.title}"`);
                } else {
                     console.warn(`  Tidak dapat menentukan metode untuk meninggalkan "${dialog.title}". Tipe entity: ${dialog.entity?.className}. Username: ${dialog.entity.username ? '@'+dialog.entity.username : 'TIDAK ADA'}`);
                }
                await new Promise(resolve => setTimeout(resolve, 2500));
            } catch (error) {
                console.error(`  Gagal meninggalkan "${dialog.title}": ${error.message}`);
                if (error.errorMessage) console.error(`  Detail Error API: ${error.errorMessage}`);
            }
        }
        console.log('\nProses meninggalkan grup/channel selesai.');
    } catch (error) {
        console.error('Terjadi kesalahan umum dalam skrip:', error.message);
        if (error.code === 401 && (error.message.includes('SESSION_REVOKED') || error.message.includes('SESSION_EXPIRED') || error.message.includes('AUTH_KEY_UNREGISTERED'))) {
            console.error("Sesi Anda tidak valid/kedaluwarsa/dicabut. Hapus file 'session.txt' dan coba jalankan lagi untuk login ulang.");
        } else if (error.message && (error.message.includes("is not a constructor") || error.message.includes("Cannot read properties of undefined"))) {
            console.error("Kesalahan kritis dengan komponen library Telegram. Pastikan library 'telegram' terinstal dengan benar.");
        }
    } finally {
        if (client && client.connected) {
            await client.disconnect();
            console.log('Koneksi ke Telegram diputus.');
        }
    }
}

main();
