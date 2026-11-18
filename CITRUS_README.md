# Valeryn untuk POCO M3 (`citrus`)

Target: **PixelOS Android 16 QPR2**, Linux arm64 **4.19.325-cip137-st21**.
Bukan paket untuk `lime` atau perangkat non-chime.

## Root dan SUSFS

- **KernelSU `backslashxx` v3.3.1+52** (`70f6aeefc2a8a358acd73c2c67383d60ca716de7`), UAPI 6, syscall-table mode.
- Prioritas: **KowSU/KOWX712**. Signature manager resmi KernelSU dan midori01 juga didukung oleh driver.
- **SUSFS 2.4.0 core** dengan supercall yang terhubung ke driver yang sama:
  `SUS_PATH`, `SUS_MOUNT`, `SUS_KSTAT`, `SPOOF_UNAME`, logging, penyetelan visibility symbol, spoof cmdline/bootconfig, `OPEN_REDIRECT`, `SUS_MAP`, dan `PRIORITY_UID_FILTER`.
- UID filter priority/ioprio dan `SUS_PATH` dipisah; daftar aplikasi diperbarui ketika `packages.list` berubah.
- **AVC log spoofing aktif secara default** dan tetap dapat di-toggle melalui SUSFS.
- SELinux hide memakai implementasi built-in backslashxx, bukan driver KSU Next.
- **NoMount v2.3.0** built-in melalui Linux key type `nomount`. Userspace NoMount pendamping tetap diperlukan untuk mengoperasikannya.

Tidak ada KSU Next ataupun manual-hook legacy yang dicampur dengan syscall-table ABI driver baru.

## Build dari VPS Ubuntu

Diperlukan Git, clang/lld, Python 3, cpio, xz, dan dependency kernel arm64 yang sesuai.

```bash
git clone -b citrus-kowsu-consolidated \
  https://github.com/LyynNotDev/valeryn_xiaomi_sm6115.git kernel-citrus
cd kernel-citrus
JOBS=2 LTO_JOBS=1 ./build-citrus.sh
```

Base config tetap `vendor/bengal-perf_defconfig`, dikombinasikan dengan `arch/arm64/configs/vendor/xiaomi/citrus.config`. ThinLTO default satu worker agar tidak membebani VPS yang RAM-nya terbatas. `OUT` dapat digunakan untuk menentukan output directory.

Artifact yang dihasilkan:
- `$OUT/Valeryn-Citrus-Image.gz-dtb`
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

Gunakan paket AnyKernel3 **hanya untuk `citrus`**, bootloader yang sesuai, dan versi PixelOS target. Backup `boot.img` aktif terlebih dahulu. Jangan flash ke `lime` atau ROM dengan vendor/kernel yang tidak cocok.

Manager prioritas: https://github.com/KOWX712/KernelSU/releases/latest
Userspace NoMount: https://github.com/maxsteeel/nomount/releases/tag/v2.3.0-720

Setelah boot, periksa versi KernelSU/KowSU, SUSFS feature bitmap/version, serta mount/UID behavior. Kompilasi berhasil tidak menggantikan pengujian root, SELinux, audio, Wi-Fi, telepon, atau stabilitas di perangkat nyata.
