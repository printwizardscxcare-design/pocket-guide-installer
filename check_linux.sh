#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  debian)
    apt-get update -qq
    apt-get install -y /artifacts/*.deb xvfb xauth
    ;;
  fedora)
    dnf install -y /artifacts/*.rpm xorg-x11-server-Xvfb xorg-x11-xauth
    ;;
  arch)
    pacman -Syu --noconfirm
    pacman -S --needed --noconfirm xorg-server-xvfb xorg-xauth
    pacman -U --noconfirm /artifacts/*.pkg.tar.gz
    ;;
esac
xvfb-run -a /opt/pocket-guide-installer/PocketGuideInstaller --smoke-test --smoke-report /tmp/pocket-check.txt
cat /tmp/pocket-check.txt
