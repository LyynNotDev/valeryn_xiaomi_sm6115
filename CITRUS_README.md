# Valeryn untuk chime (`citrus` + `lime`)

Basis: Linux arm64 **4.19.325-cip137-st21** untuk keluarga Xiaomi SM6115.
Target yang sudah dipakai sebelumnya: **PixelOS Android 16 QPR2 pada citrus**. Dukungan lime dan ROM/Android versi lain tetap memerlukan pengujian perangkat; kompilasi bukan bukti boot atau kompatibilitas vendor.

## Root dan SUSFS

- **BakaSU `35289`** (`99ff0a27ca5477180da6d70e7387b91b0a9aa5b7`, `v4.2.0-rc3`), UAPI 6, menggunakan SUSFS inline hook pada kernel 4.19. Termasuk fallback upstream `4ca505a8` ketika metadata `is_original_xxx` tidak tersedia.
- Manager yang sesuai: **BakaSU Manager `35289/6`**. Referensi Manager dan driver memakai revisi upstream yang sama. Dukungan multi-manager dari driver tetap mengikuti implementasi upstream BakaSU; jangan mencampur daemon/manager lama dan menganggap hasilnya terverifikasi.
- **SUSFS 2.4.0 core** dengan supercall yang terhubung ke driver yang sama:
  `SUS_PATH`, `SUS_MOUNT`, `SUS_KSTAT`, `SPOOF_UNAME`, logging, penyetelan visibility symbol, spoof cmdline/bootconfig, `OPEN_REDIRECT`, `SUS_MAP`, dan `PRIORITY_UID_FILTER`.
- UID filter priority/ioprio dan `SUS_PATH` dipisah; daftar aplikasi diperbarui ketika `packages.list` berubah.
- **AVC log spoofing aktif secara default** dan tetap dapat di-toggle melalui SUSFS.
- SELinux hide memakai implementasi built-in BakaSU.
- **NoMount API 23 + dev** (`87b05967532a039f5d3bea660eadcabed43d3e71`) built-in melalui Linux key type `nomount`. Termasuk pemeriksaan backing inode dan pin native parent dengan full path. Userspace NoMount pendamping tetap diperlukan untuk mengoperasikannya.

Classic `su` melalui `/system/bin/su` dialihkan oleh sucompat ke `ksud`. Regression test menjaga cabang `execve` setelah storage decrypted agar tidak lagi terlewat; verifikasi pada perangkat untuk kandidat final adalah `su -c id` menghasilkan `uid=0(root)` dan `nm version` menghasilkan `23`.

## Build dari VPS Ubuntu

Diperlukan Git, clang/lld, Python 3, cpio, xz, dan dependency kernel arm64 yang sesuai.

```bash
git clone -b bakasu-sucompat-release \
  https://github.com/LyynNotDev/valeryn_xiaomi_sm6115.git kernel-chime
cd kernel-chime
# POCO M3
DEVICE=citrus JOBS=2 LTO_JOBS=1 ./build-chime.sh
# Redmi 9T / Note 9 4G (lime)
DEVICE=lime JOBS=2 LTO_JOBS=1 ./build-chime.sh
```

`./build-citrus.sh` tetap tersedia sebagai wrapper yang setara dengan `DEVICE=citrus ./build-chime.sh`.

Base config tetap `vendor/bengal-perf_defconfig`, dikombinasikan dengan `chime.config` untuk fitur bersama dan `citrus.config`/`lime.config` untuk pemilihan board. Output default dipisahkan ke `out/citrus` dan `out/lime`. ThinLTO default satu worker agar tidak membebani VPS yang RAM-nya terbatas. `OUT` dapat digunakan untuk menentukan output directory.

Artifact yang dihasilkan per board:
- `$OUT/Image.gz`
- `$OUT/dtb.img`
- `$OUT/dtbo.img`
- `$OUT/Valeryn-Citrus-Image.gz-dtb` atau `$OUT/Valeryn-Lime-Image.gz-dtb`
- `$OUT/SHA256SUMS`
- `$OUT/.config` untuk mengecek opsi build yang aktual

## Audio – yang sudah dan belum dibuktikan

Audio dari Greenforce `qti-perf` dibandingkan pada commit `eb71a500beb14544978f5d45f593c29e0429b0ab`. Yang dipilih hanya penggereman race pada `msm_compr_volume_put()`/lifecycle stream. Perubahan headset-button, wake-lock listener, serta penghapusan upstream fix tidak ikut diimpor.

**Keluhan speaker noise/gembret dan suara speaker kembali ke mic saat call/game belum terbukti selesai di hardware.** Jalur tersebut bergantung pada opsi DMIC, echo-reference ke ADM, ACDB/AEC/NS, mixer PixelOS, dan firmware Awinic; tidak boleh diasumsikan beres hanya dari compile.

Hasilkan capture setelah reproduksi dengan ADB:

```bash
./tools/audio/collect-citrus-audio.sh
```

Skrip hanya membaca kondisi; tidak mengubah mixer atau gain. Periksa informasi pribadi sebelum membagikan arsip hasilnya.

## Flash dan verifikasi

Frontend universal dikelola terpisah di repository privat **`LyynNotDev/valeryn-chime-anykernel3`**, bukan di repository kernel ini. Repository companion itu membawa `anykernel.sh`, runtime AnyKernel3, serta source `anykernel/chime.sh` yang diuji. ZIP chime membawa `boards/citrus/{dtb.img,dtbo.img}` dan `boards/lime/{dtb.img,dtbo.img}`; script memilih payload dari properti perangkat sebelum `dump_boot`/`write_boot`. Device check hanya menerima `citrus` dan `lime`. Jangan memakai satu DTBO untuk kedua board.

Setelah kedua build selesai, gunakan packager dari checkout companion tersebut:

```bash
python3 tools/package-chime.py \
  --template /path/ke/Valeryn-Citrus-Template.zip \
  --citrus-out out/citrus \
  --lime-out out/lime \
  --output out/Valeryn-Chime.zip
```

Packager menolak payload yang rusak atau `.config` yang berbeda selain pemilihan board, sehingga satu `Image.gz` tidak diam-diam dipakai untuk dua fitur kernel yang tidak setara.

`supported.versions=12 - 17` adalah batas versi yang diterima installer, bukan klaim bahwa semua ROM Android 12–17 sudah kompatibel. Tidak ada guard Android-16-only di kernel tree, tetapi setiap ROM tetap bergantung pada device tree, VINTF, vendor blobs, HAL, dan format boot yang dipakai. Backup `boot.img` dan `dtbo.img` aktif sebelum flash. Pengujian nyata diperlukan pada setiap board dan ROM; jangan anggap Android 12–17 atau lime sudah terverifikasi hanya karena ZIP berhasil dibuat.

Manager BakaSU: https://github.com/Baka-SU/BakaSU
Userspace NoMount (dev): https://github.com/maxsteeel/nomount/tree/dev

Setelah boot, periksa versi BakaSU Manager/driver, SUSFS feature bitmap/version, `su -c id`, dan `nm version`. Kompilasi berhasil tidak menggantikan pengujian root, SELinux, audio, Wi-Fi, telepon, atau stabilitas di perangkat nyata.
