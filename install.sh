#!/usr/bin/env bash
# Supernet — one-command installer
# Usage: cd /path/to/install && curl -fsSL https://raw.githubusercontent.com/Gao-Haodong/supernet/main/install.sh | bash
set -e

VERSION="1.3.1"
# Install to current directory. cd to your desired location first.
INSTALL_DIR="$(pwd)"
PYTHON=""

# Detect Python
for cmd in python3 python; do
    if command -v $cmd &>/dev/null; then
        PYTHON=$cmd
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.8+ is required. Install it first."
    exit 1
fi

echo "=== Supernet v${VERSION} Installer ==="
echo ""

# 1. Create directory
mkdir -p "${INSTALL_DIR}/script"

# 2. Install Python packages
echo "[1/3] Installing Python dependencies..."
$PYTHON -m pip install yt-dlp trafilatura feedparser qrcode[pil] -q 2>/dev/null || {
    echo "Warning: pip install failed. Run manually: pip install yt-dlp trafilatura feedparser qrcode[pil]"
}

# 3. Check ffmpeg
echo "[2/3] Checking ffmpeg..."
if command -v ffmpeg &>/dev/null; then
    echo "  ffmpeg found: $(which ffmpeg)"
else
    echo "  ffmpeg not found. Audio conversion requires ffmpeg."
    echo "  Download: https://ffmpeg.org/download.html"
fi

# 4. Create .env template
echo "[3/3] Creating .env template..."
if [ ! -f "${INSTALL_DIR}/.env" ]; then
    cat > "${INSTALL_DIR}/.env" << 'EOF'
# Supernet proxy config (auto-loaded)
# PROXY_POOL=http://user:pass@proxy1:port,http://user:pass@proxy2:port
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
EOF
    echo "  Created .env at ${INSTALL_DIR}/.env"
else
    echo "  .env already exists, skipping"
fi

# 5. Verify
echo ""
echo "=== Installation complete ==="
echo "  Location: ${INSTALL_DIR}"
echo "  Python:   ${PYTHON}"
echo "  Version:  ${VERSION}"
echo ""
echo "Quick test:"
echo "  cd ${INSTALL_DIR}/script"
echo "  ${PYTHON} supernet.py --version"
echo "  ${PYTHON} supernet.py qr https://example.com"
echo ""
echo ""
echo "Files installed to: ${INSTALL_DIR}"
echo ""
