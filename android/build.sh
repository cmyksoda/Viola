#!/usr/bin/env bash
# Builds the APK without Gradle, straight from the SDK tools.
# Signs with the release key when VIOLA_KEYSTORE, VIOLA_KEYSTORE_PASS, VIOLA_KEY_ALIAS and VIOLA_KEY_PASS are set,
# and with the SDK's debug key otherwise.
set -euo pipefail
cd "$(dirname "$0")"
sdk="${ANDROID_HOME:-$HOME/Android/Sdk}"
tools="$sdk/build-tools/$(ls "$sdk/build-tools" | sort -V | tail -1)"
jar="$sdk/platforms/$(ls "$sdk/platforms" | sort -V | tail -1)/android.jar"
version=$(sed -n 's/.*android:versionName="\([^"]*\)".*/\1/p' AndroidManifest.xml)
out=build

rm -rf "$out" && mkdir -p "$out/res" "$out/classes" "$out/gen"
cp -r res/. "$out/res/"
python3 -I ../tools/themes.py --android "$out"
sed "/<!-- theme icon aliases -->/r $out/aliases.xml" AndroidManifest.xml > "$out/AndroidManifest.xml"
for pair in mdpi:48 hdpi:72 xhdpi:96 xxhdpi:144 xxxhdpi:192; do
    dir="$out/res/mipmap-${pair%%:*}"
    mkdir -p "$dir"
    inkscape ../web/icon.svg -w "${pair##*:}" -h "${pair##*:}" -o "$dir/ic_launcher.png" 2>/dev/null
    cp "$dir/ic_launcher.png" "$dir/ic_launcher_round.png"
done

"$tools/aapt2" compile --dir "$out/res" -o "$out/res.zip"
"$tools/aapt2" link -I "$jar" --manifest "$out/AndroidManifest.xml" --min-sdk-version 24 --target-sdk-version 34 \
    --java "$out/gen" -o "$out/unsigned.apk" "$out/res.zip"
javac -source 11 -target 11 -Xlint:-options -classpath "$jar" -d "$out/classes" \
    $(find src "$out/gen" -name '*.java')
"$tools/d8" --min-api 24 --lib "$jar" --output "$out" $(find "$out/classes" -name '*.class')
(cd "$out" && zip -q unsigned.apk classes.dex)
"$tools/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
if [ -n "${VIOLA_KEYSTORE:-}" ]; then
    "$tools/apksigner" sign --ks "$VIOLA_KEYSTORE" --ks-pass env:VIOLA_KEYSTORE_PASS \
        --ks-key-alias "$VIOLA_KEY_ALIAS" --key-pass env:VIOLA_KEY_PASS \
        --out "$out/viola-$version.apk" "$out/aligned.apk"
else
    "$tools/apksigner" sign --ks "$HOME/.android/debug.keystore" --ks-pass pass:android \
        --out "$out/viola-$version.apk" "$out/aligned.apk"
fi
echo "$out/viola-$version.apk"
