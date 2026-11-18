#!/usr/bin/env bash
# Read-only audio diagnostics for Xiaomi chime/citrus on Android.
# Use while the problematic call/game voice route has just reproduced the issue.
set -u
ADB="${ADB:-adb}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${1:-citrus-audio-${STAMP}}"
mkdir -p "$DEST" || exit 1
: > "$DEST/command-status.txt"

"$ADB" get-state > "$DEST/device-state.txt" 2>&1 || {
    printf 'No authorized ADB device is available. Check USB debugging and authorization.\n' >&2
    exit 1
}

capture() {
    local label="$1"
    shift
    printf '\n[%s] %s\n' "$label" "$*" >> "$DEST/command-status.txt"
    "$@" > "$DEST/${label}.txt" 2>> "$DEST/command-status.txt"
    local rc=$?
    printf 'exit=%s\n' "$rc" >> "$DEST/command-status.txt"
}

capture getprop "$ADB" shell getprop
capture audio_flinger "$ADB" shell dumpsys media.audio_flinger
capture audio_policy "$ADB" shell dumpsys media.audio_policy
capture asound_cards "$ADB" shell cat /proc/asound/cards
capture logcat_audio "$ADB" logcat -d -v threadtime -t 6000 -s audio_hw_primary:V msm8974_platform:V audio_route:V AudioFlinger:V AudioPolicyManager:V

# Mixer and dmesg normally require root. Never silently fall back and claim
# complete results when root is unavailable.
if "$ADB" shell su -c id > "$DEST/root-identity.txt" 2>&1; then
    capture dmesg "$ADB" shell su -c dmesg
    capture tinymix "$ADB" shell su -c tinymix
else
    capture dmesg-unprivileged "$ADB" shell dmesg
    printf 'Root is unavailable: dmesg/tinymix may be incomplete.\n' | tee -a "$DEST/command-status.txt"
fi

cat > "$DEST/README.txt" <<'EOF'
Focus review on:
- aw87359/aw87519 failures, I2C errors and SWR overflow/underflow
- selected input/output device, ACDB ID and capture format/channel rate
- TX DMIC MUX*, TX_DEC*, AUDIO_REF_EC_UL10 MUX and sidetone
- AEC/NS effect-chain state and active voip/call input source

The script only reads state; it does not change gain, routing or effects.
Review logs for private app/account information before sharing them.
EOF

TAR_FILE="${DEST}.tar.gz"
tar -czf "$TAR_FILE" "$DEST" && printf 'Diagnostics: %s\n' "$TAR_FILE"
