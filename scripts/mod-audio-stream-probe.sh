#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-receptify}"
MODE="${1:-enable}"
TEXT="${MOD_AUDIO_STREAM_PROBE_TEXT:-This is a mod audio stream playback test.}"
KUBECTL="${KUBECTL:-kubectl}"

case "$MODE" in
  enable)
    "$KUBECTL" set env -n "$NAMESPACE" deployment/agent \
      AUDIO_PLAYBACK_MODE=mod_audio_stream \
      MOD_AUDIO_STREAM_PROBE_TEXT="$TEXT"
    "$KUBECTL" rollout status -n "$NAMESPACE" deployment/agent
    ;;
  disable)
    "$KUBECTL" set env -n "$NAMESPACE" deployment/agent \
      AUDIO_PLAYBACK_MODE- \
      MOD_AUDIO_STREAM_PROBE_TEXT-
    "$KUBECTL" rollout status -n "$NAMESPACE" deployment/agent
    ;;
  status)
    "$KUBECTL" exec -n "$NAMESPACE" deployment/agent -- printenv AUDIO_PLAYBACK_MODE || true
    "$KUBECTL" exec -n "$NAMESPACE" deployment/agent -- printenv MOD_AUDIO_STREAM_PROBE_TEXT || true
    ;;
  *)
    echo "Usage: $0 enable|disable|status" >&2
    exit 2
    ;;
esac
