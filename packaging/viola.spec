Name:           viola
Version:        %{viola_version}
Release:        1
Summary:        A claude.ai-style window for Claude Code on API credits
License:        GPL-3.0-or-later AND OFL-1.1 AND Cronyx
URL:            https://github.com/cmyksoda/Viola
BuildArch:      noarch
Requires:       python3 >= 3.10
Requires:       python3-gobject
Requires:       gtk3
Requires:       webkit2gtk4.1
Recommends:     libnotify

%description
Viola runs Claude Code in a desktop window styled after claude.ai, with a
sidebar of chats, a model and effort picker, and a credit counter. It needs
Claude Code and an Anthropic API key, and can be opened from a phone over
Tailscale.

%install
cp -a %{viola_root}/. %{buildroot}/

%changelog
* Wed Oct 28 2026 Jaxi - 1.0.0-1
- First public release: macOS and Windows support, licenses

* Sat Oct 24 2026 Jaxi - 0.1.0-1
- First package

%files
/usr/bin/viola
/usr/lib/viola
/usr/share/applications/viola.desktop
/usr/share/icons/hicolor/*/apps/viola.*
%doc /usr/share/doc/viola/README.md
%license /usr/share/licenses/viola
