#!/usr/bin/env bash
# Builds Viola's .rpm and .deb. Without dpkg-deb on the host, the .deb is built inside a Debian container.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
version="$(cat "$here/VERSION")"
out="$here/packaging/build"
root="$out/root"

rm -rf "$out" && mkdir -p "$root/usr/lib/viola" "$root/usr/bin" "$root/usr/share/applications" \
    "$root/usr/share/icons/hicolor/scalable/apps" "$root/usr/share/doc/viola"
cp "$here/viola.py" "$here/server.py" "$here/sessions.py" "$here/VERSION" "$root/usr/lib/viola/"
cp -r "$here/web" "$root/usr/lib/viola/"
printf '#!/bin/sh\nexec python3 /usr/lib/viola/viola.py "$@"\n' > "$root/usr/bin/viola"
chmod 755 "$root/usr/bin/viola"
sed "s|python3 @APP@|viola|" "$here/viola.desktop" > "$root/usr/share/applications/viola.desktop"
cp "$here/web/icon.svg" "$root/usr/share/icons/hicolor/scalable/apps/viola.svg"
python3 "$here/tools/icons.py" "$root/usr/share/icons/hicolor"
cp "$here/README.md" "$root/usr/share/doc/viola/"
mkdir -p "$root/usr/share/licenses/viola"
cp "$here/LICENSE" "$here/licenses/"* "$root/usr/share/licenses/viola/"

rpmbuild -bb --quiet --define "_topdir $out/rpm" --define "viola_version $version" \
    --define "viola_root $root" "$here/packaging/viola.spec"
cp "$out"/rpm/RPMS/noarch/viola-*.rpm "$out/"

mkdir -p "$out/deb/DEBIAN"
cp -a "$root/." "$out/deb/"
cat > "$out/deb/DEBIAN/control" <<CONTROL
Package: viola
Version: $version
Architecture: all
Maintainer: Jaxi <cmyksoda@users.noreply.github.com>
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1
Recommends: libnotify-bin
Section: net
Priority: optional
Description: A claude.ai-style window for Claude Code on API credits
 Viola runs Claude Code in a desktop window styled after claude.ai, with a
 sidebar of chats, a model and effort picker, and a credit counter.
CONTROL
if command -v dpkg-deb >/dev/null; then
    dpkg-deb --root-owner-group --build "$out/deb" "$out/viola_${version}_all.deb" >/dev/null
else
    docker run --rm -v "$out:/out" debian:trixie \
        sh -c "dpkg-deb --root-owner-group --build /out/deb /out/viola_${version}_all.deb >/dev/null && chown $(id -u):$(id -g) /out/viola_${version}_all.deb"
fi

ls -1 "$out"/*.rpm "$out"/*.deb
