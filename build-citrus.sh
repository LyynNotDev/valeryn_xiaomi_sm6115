#!/usr/bin/env bash
# Reproducible POCO M3 (citrus) legacy arm64 kernel build.
set -Eeuo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUT="${OUT:-${SOURCE_DIR}/out/citrus}"
JOBS="${JOBS:-2}"
LTO_JOBS="${LTO_JOBS:-1}"
LD="${LD:-ld.lld --thinlto-jobs=${LTO_JOBS}}"
PYTHON="$(command -v python3)"
BUILD=(make -C "${SOURCE_DIR}" O="${OUT}" ARCH=arm64 LLVM=1 LLVM_IAS=1 LD="${LD}" PYTHON="${PYTHON}")
DEFCONFIG="vendor/bengal-perf_defconfig"
FRAGMENT="${SOURCE_DIR}/arch/arm64/configs/vendor/xiaomi/citrus.config"

command -v clang >/dev/null
command -v cpio >/dev/null
command -v xz >/dev/null
mkdir -p "${OUT}"

"${BUILD[@]}" "${DEFCONFIG}"
"${SOURCE_DIR}/scripts/kconfig/merge_config.sh" \
    -O "${OUT}" -m "${OUT}/.config" "${FRAGMENT}"
"${BUILD[@]}" olddefconfig

for option in \
    CONFIG_BOARD_CITRUS=y \
    CONFIG_KSU=y \
    CONFIG_KSU_TAMPER_SYSCALL_TABLE=y \
    CONFIG_KSU_SUSFS=y \
    CONFIG_KSU_SUSFS_SUS_PATH=y \
    CONFIG_KSU_SUSFS_SUS_MOUNT=y \
    CONFIG_KSU_SUSFS_SUS_KSTAT=y \
    CONFIG_KSU_SUSFS_SPOOF_UNAME=y \
    CONFIG_KSU_SUSFS_ENABLE_LOG=y \
    CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y \
    CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y \
    CONFIG_KSU_SUSFS_OPEN_REDIRECT=y \
    CONFIG_KSU_SUSFS_SUS_MAP=y \
    CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y \
    CONFIG_NOMOUNT=y \
    CONFIG_KEYS=y; do
    if ! grep -Fqx "${option}" "${OUT}/.config"; then
        printf 'Required option missing: %s\n' "${option}" >&2
        exit 1
    fi
done

"${BUILD[@]}" -j"${JOBS}" Image.gz-dtb dtb dtbo.img
IMAGE="${OUT}/arch/arm64/boot/Image.gz"
APPENDED_IMAGE="${OUT}/arch/arm64/boot/Image.gz-dtb"
DTB="${OUT}/arch/arm64/boot/dtb"
DTBO="${OUT}/arch/arm64/boot/dtbo.img"
for artifact in "${IMAGE}" "${APPENDED_IMAGE}" "${DTB}" "${DTBO}"; do
    test -s "${artifact}"
done

# Valeryn's frontend replaces boot DTB and flashes dtbo.img directly.
cp -f "${IMAGE}" "${OUT}/Image.gz"
cp -f "${APPENDED_IMAGE}" "${OUT}/Valeryn-Citrus-Image.gz-dtb"
cp -f "${DTB}" "${OUT}/dtb.img"
cp -f "${DTBO}" "${OUT}/dtbo.img"
(
    cd "${OUT}"
    sha256sum Image.gz dtb.img dtbo.img Valeryn-Citrus-Image.gz-dtb > SHA256SUMS
)
printf 'Valeryn kernel payload: %s\n' "${OUT}/Image.gz"
printf 'Boot DTB: %s\n' "${OUT}/dtb.img"
printf 'Android DT_TABLE overlay image: %s\n' "${OUT}/dtbo.img"
