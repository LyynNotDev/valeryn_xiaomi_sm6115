#!/usr/bin/env bash
# Reproducible POCO M3 (citrus) legacy arm64 kernel build.
set -Eeuo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUT="${OUT:-${SOURCE_DIR}/out/citrus}"
JOBS="${JOBS:-2}"
LTO_JOBS="${LTO_JOBS:-1}"
LD="${LD:-ld.lld --thinlto-jobs=${LTO_JOBS}}"
BUILD=(make -C "${SOURCE_DIR}" O="${OUT}" ARCH=arm64 LLVM=1 LLVM_IAS=1 LD="${LD}")
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

"${BUILD[@]}" -j"${JOBS}" Image.gz-dtb
IMAGE="${OUT}/arch/arm64/boot/Image.gz-dtb"
test -s "${IMAGE}"

cp -f "${IMAGE}" "${OUT}/Valeryn-Citrus-Image.gz-dtb"
sha256sum "${OUT}/Valeryn-Citrus-Image.gz-dtb" > "${OUT}/SHA256SUMS"
printf 'Citrus kernel image: %s\n' "${OUT}/Valeryn-Citrus-Image.gz-dtb"
