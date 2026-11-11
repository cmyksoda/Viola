package io.github.cmyksoda.viola;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ComponentName;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Insets;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.Locale;

public class ViolaActivity extends Activity {
    private static final String PREFS = "viola";
    private static final String KEY_URL = "url";
    private static final String KEY_DARK = "dark";
    private static final String KEY_GROUND = "ground";
    private static final String KEY_ACCENT = "accent";
    private static final String KEY_ICON = "icon";
    private static final String KEY_ICON_SHOWN = "icon_shown";
    private static final String CLASSIC_ICON = "ClassicIcon";
    private static final int GROUND = Color.rgb(0x26, 0x26, 0x24);
    private static final int PAPER = Color.rgb(0xfa, 0xf9, 0xf5);
    private static final int FIELD = Color.rgb(0x30, 0x30, 0x2e);
    private static final int TEXT = Color.rgb(0xfa, 0xf9, 0xf5);
    private static final int MUTED = Color.rgb(0x9c, 0x9a, 0x92);
    private static final int CLAY = Color.rgb(0xd9, 0x77, 0x57);
    private static final int PICK_FILES = 1;

    private FrameLayout root;
    private View setup;
    private WebView web;
    private String url;
    private boolean dark;
    private int ground;
    private int insetTop, insetBottom, insetLeft, insetRight;
    private ValueCallback<Uri[]> filesCallback;
    private Uri photoUri;

    @Override
    protected void onCreate(Bundle state) {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        // The text-selection handles take their color from the theme's accent.
        String accent = "ViolaAccent_" + prefs.getString(KEY_ACCENT, "clay_dark");
        int style = getResources().getIdentifier(accent, "style", getPackageName());
        if (style != 0) setTheme(style);
        super.onCreate(state);

        dark = prefs.getBoolean(KEY_DARK, true);
        ground = prefs.getInt(KEY_GROUND, dark ? GROUND : PAPER);

        drawBehindBars();
        root = new FrameLayout(this);
        root.setOnApplyWindowInsetsListener((view, insets) -> applyInsets(insets));
        setContentView(root);
        applyBars(dark);
        paintGround();

        url = prefs.getString(KEY_URL, null);
        String shared = sharedLink(getIntent());
        if (url == null && shared != null) url = saveUrl(shared);
        if (url == null) showSetup(null);
        else showWeb(state);
        if (shared != null && !shared.equals(url)) confirmLink(shared);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        String shared = sharedLink(intent);
        if (shared == null || shared.equals(url)) return;
        if (url != null) {
            confirmLink(shared);
            return;
        }
        url = saveUrl(shared);
        showWeb(null);
    }

    // Any app can share a link with Viola, so one that would replace the saved link waits for the user to agree.
    private void confirmLink(String shared) {
        new AlertDialog.Builder(this, android.R.style.Theme_Material_Dialog_Alert)
                .setTitle("Use this link?")
                .setMessage("Viola would open " + Uri.parse(shared).getHost() + " from now on. It opens "
                        + Uri.parse(url).getHost() + " now.")
                .setPositiveButton("Use it", (d, w) -> {
                    url = saveUrl(shared);
                    showWeb(null);
                })
                .setNegativeButton("Keep the old one", null)
                .show();
    }

    // Viola's page paints under the status and navigation bars, so the sidebar and dimmed sheets reach the edges.
    private void drawBehindBars() {
        Window window = getWindow();
        window.setStatusBarColor(Color.TRANSPARENT);
        window.setNavigationBarColor(Color.TRANSPARENT);
        if (Build.VERSION.SDK_INT >= 29) {
            window.setStatusBarContrastEnforced(false);
            window.setNavigationBarContrastEnforced(false);
        }
        if (Build.VERSION.SDK_INT >= 28) {
            WindowManager.LayoutParams params = window.getAttributes();
            params.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            window.setAttributes(params);
        }
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false);
        } else {
            window.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
    }

    private WindowInsets applyInsets(WindowInsets insets) {
        int keyboard;
        if (Build.VERSION.SDK_INT >= 30) {
            Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            keyboard = insets.getInsets(WindowInsets.Type.ime()).bottom;
            insetTop = bars.top;
            insetBottom = bars.bottom;
            insetLeft = bars.left;
            insetRight = bars.right;
        } else {
            insetTop = insets.getSystemWindowInsetTop();
            insetBottom = insets.getSystemWindowInsetBottom();
            insetLeft = insets.getSystemWindowInsetLeft();
            insetRight = insets.getSystemWindowInsetRight();
            // Before Android 11 the keyboard only shows up as a tall bottom inset.
            keyboard = insetBottom > getResources().getDisplayMetrics().heightPixels / 6 ? insetBottom : 0;
        }

        // The keyboard slides over the page, which makes room through --inset-bottom in its own colors;
        // shrinking the page instead showed the native backing in the gap while the keyboard moved.
        if (keyboard > 0) insetBottom = keyboard;
        if (setup != null) {
            setup.setPadding(dp(28) + insetLeft, dp(28) + insetTop, dp(28) + insetRight, dp(28) + insetBottom);
        }

        pushInsets();
        return Build.VERSION.SDK_INT >= 30 ? WindowInsets.CONSUMED : insets.consumeSystemWindowInsets();
    }

    private void pushInsets() {
        if (web == null) return;
        float density = getResources().getDisplayMetrics().density;
        String js = String.format(Locale.ROOT,
                "(function(s){s.setProperty('--inset-top','%.1fpx');s.setProperty('--inset-bottom','%.1fpx');"
                        + "s.setProperty('--inset-left','%.1fpx');s.setProperty('--inset-right','%.1fpx');})"
                        + "(document.documentElement.style)",
                insetTop / density, insetBottom / density, insetLeft / density, insetRight / density);
        web.evaluateJavascript(js, null);
    }

    private void applyBars(boolean isDark) {
        dark = isDark;
        Window window = getWindow();
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController controller = window.getInsetsController();
            int light = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                    | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
            if (controller != null) controller.setSystemBarsAppearance(isDark ? 0 : light, light);
        } else {
            View decor = window.getDecorView();
            int light = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
                    | (Build.VERSION.SDK_INT >= 26 ? View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR : 0);
            int flags = decor.getSystemUiVisibility();
            decor.setSystemUiVisibility(isDark ? flags & ~light : flags | light);
        }
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putBoolean(KEY_DARK, isDark).apply();
    }

    // Only before the page shows: repainting these under a live WebView left ghost images after theme changes.
    private void paintGround() {
        root.setBackgroundColor(ground);
        getWindow().getDecorView().setBackgroundColor(ground);
    }

    private class Bridge {
        @JavascriptInterface
        public void setDark(boolean isDark) {
            runOnUiThread(() -> {
                if (isDark != dark) applyBars(isDark);
            });
        }

        // Also saved, so the next launch starts with this accent.
        @JavascriptInterface
        public void setAccent(String themeId) {
            String key = themeId.replace('-', '_');
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_ACCENT, key).apply();
            int style = getResources().getIdentifier("ViolaAccent_" + key, "style", getPackageName());
            // Handles drawn after this use the new accent; any already on screen keep the old one.
            if (style != 0) runOnUiThread(() -> getTheme().applyStyle(style, true));
        }

        // An empty theme means the classic icon.
        @JavascriptInterface
        public void setIcon(String themeId) {
            String icon = themeId.isEmpty() || Build.VERSION.SDK_INT < 26
                    ? CLASSIC_ICON
                    : "Icon_" + themeId.replace('-', '_');
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_ICON, icon).apply();
        }

        // The WebView's own backdrop follows the theme so a repaint never flashes the old color; the root and
        // window backgrounds are only painted at launch, since repainting those under the live page left ghosts.
        @JavascriptInterface
        public void setGround(int rgb) {
            int color = 0xff000000 | rgb;
            getSharedPreferences(PREFS, MODE_PRIVATE).edit().putInt(KEY_GROUND, color).apply();
            runOnUiThread(() -> {
                if (web != null) web.setBackgroundColor(color);
            });
        }
    }

    private String sharedLink(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return null;
        String text = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (text == null) return null;
        // Only a Viola link carries its token; anything else shared here is ignored.
        Uri link = Uri.parse(text.trim());
        boolean web = "http".equals(link.getScheme()) || "https".equals(link.getScheme());
        String fragment = link.getFragment();
        return web && link.getHost() != null && fragment != null && fragment.startsWith("token=") ? text.trim() : null;
    }

    private String saveUrl(String value) {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString(KEY_URL, value).apply();
        return value;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private GradientDrawable rounded(int color, int radius) {
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(color);
        shape.setCornerRadius(dp(radius));
        return shape;
    }

    private void showSetup(String problem) {
        applyBars(true);
        paintGround();
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER_VERTICAL);
        box.setBackgroundColor(GROUND);

        TextView title = new TextView(this);
        title.setText("Viola");
        title.setTextColor(TEXT);
        title.setTextSize(36);
        title.setTypeface(Typeface.SERIF);
        box.addView(title);

        TextView hint = new TextView(this);
        hint.setText(problem != null ? problem
                : "Paste the link from Viola's Settings → Remote on your computer. The phone needs Tailscale, or the same Wi-Fi as the computer.");
        hint.setTextColor(problem != null ? CLAY : MUTED);
        hint.setTextSize(15);
        hint.setLineSpacing(0, 1.2f);
        hint.setPadding(0, dp(10), 0, dp(22));
        box.addView(hint);

        EditText field = new EditText(this);
        field.setHint("https://…ts.net:47818/#token=…");
        field.setTextColor(TEXT);
        field.setHintTextColor(MUTED);
        field.setSingleLine(true);
        field.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
        field.setBackground(rounded(FIELD, 14));
        field.setPadding(dp(16), dp(14), dp(16), dp(14));
        if (url != null) field.setText(url);
        box.addView(field);

        Button go = new Button(this);
        go.setText("Connect");
        go.setAllCaps(false);
        go.setTextSize(16);
        go.setTextColor(Color.WHITE);
        go.setBackground(rounded(CLAY, 14));
        go.setStateListAnimator(null);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(52));
        lp.topMargin = dp(14);
        box.addView(go, lp);
        go.setOnClickListener(v -> {
            String value = field.getText().toString().trim();
            if (!value.startsWith("http")) {
                field.setError("That should start with https://");
                return;
            }
            url = saveUrl(value);
            showWeb(null);
        });

        web = null;
        setup = box;
        root.removeAllViews();
        root.addView(box, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        root.requestApplyInsets();
    }

    private void showWeb(Bundle state) {
        setup = null;
        web = new WebView(this);
        web.setBackgroundColor(ground);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.addJavascriptInterface(new Bridge(), "ViolaAndroid");

        final String origin = Uri.parse(url).getHost();
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri target = request.getUrl();
                if (origin != null && origin.equals(target.getHost())) return false;
                startActivity(new Intent(Intent.ACTION_VIEW, target));
                return true;
            }

            @Override
            public void onPageCommitVisible(WebView view, String loaded) {
                pushInsets();
            }

            @Override
            public void onPageFinished(WebView view, String loaded) {
                pushInsets();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) offline(String.valueOf(error.getDescription()));
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (filesCallback != null) filesCallback.onReceiveValue(null);
                filesCallback = callback;
                photoUri = null;
                try {
                    startActivityForResult(pickerIntent(params), PICK_FILES);
                    return true;
                } catch (ActivityNotFoundException | IllegalArgumentException | SecurityException e) {
                    dropPhoto();
                    filesCallback = null;
                    return false;
                }
            }
        });

        root.removeAllViews();
        root.addView(web, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        root.requestApplyInsets();
        if (state != null) web.restoreState(state);
        else web.loadUrl(url);
    }

    private Intent pickerIntent(WebChromeClient.FileChooserParams params) {
        boolean images = params.getAcceptTypes().length > 0;
        for (String type : params.getAcceptTypes()) images &= type.startsWith("image/");
        boolean multiple = params.getMode() == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE;

        if (images && params.isCaptureEnabled()) {
            // The camera saves into Pictures/Viola, an entry this app owns, so the page can read the photo back.
            ContentValues values = new ContentValues();
            values.put(MediaStore.Images.Media.DISPLAY_NAME, "viola-" + System.currentTimeMillis() + ".jpg");
            values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
            if (Build.VERSION.SDK_INT >= 29) values.put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/Viola");
            photoUri = getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
            Intent camera = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            camera.putExtra(MediaStore.EXTRA_OUTPUT, photoUri);
            camera.setClipData(ClipData.newRawUri("", photoUri));
            camera.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            return camera;
        }
        if (images && Build.VERSION.SDK_INT >= 33) {
            Intent picker = new Intent(MediaStore.ACTION_PICK_IMAGES);
            if (multiple) picker.putExtra(MediaStore.EXTRA_PICK_IMAGES_MAX, MediaStore.getPickImagesMaxLimit());
            return picker;
        }
        Intent intent = params.createIntent();
        if (multiple) intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
        return intent;
    }

    private void dropPhoto() {
        if (photoUri != null) getContentResolver().delete(photoUri, null, null);
        photoUri = null;
    }

    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        if (request != PICK_FILES || filesCallback == null) {
            super.onActivityResult(request, result, data);
            return;
        }

        Uri[] picked = null;
        if (result != RESULT_OK) {
            dropPhoto();
        } else if (photoUri != null) {
            picked = new Uri[] {photoUri};
        } else if (data != null && data.getClipData() != null) {
            ClipData clip = data.getClipData();
            picked = new Uri[clip.getItemCount()];
            for (int i = 0; i < picked.length; i++) picked[i] = clip.getItemAt(i).getUri();
        } else if (data != null && data.getData() != null) {
            picked = new Uri[] {data.getData()};
        }

        filesCallback.onReceiveValue(picked);
        filesCallback = null;
        photoUri = null;
    }

    private void offline(String why) {
        new AlertDialog.Builder(this, android.R.style.Theme_Material_Dialog_Alert)
                .setTitle("Can't reach Viola")
                .setMessage("Check that Viola is running on your computer, and that this phone is on Tailscale or the same Wi-Fi.\n\n("
                        + why + ")")
                .setPositiveButton("Retry", (d, w) -> web.loadUrl(url))
                .setNeutralButton("Change link", (d, w) -> showSetup(null))
                .setCancelable(false)
                .show();
    }

    @Override
    protected void onStop() {
        super.onStop();
        swapIcon();
    }

    // Android can close an app whose launcher entry changes, so the icon only swaps once Viola is in the background.
    private void swapIcon() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String wanted = prefs.getString(KEY_ICON, CLASSIC_ICON);
        String shown = prefs.getString(KEY_ICON_SHOWN, CLASSIC_ICON);
        if (wanted.equals(shown)) return;
        PackageManager pm = getPackageManager();
        try {
            pm.setComponentEnabledSetting(new ComponentName(this, getPackageName() + "." + wanted),
                    PackageManager.COMPONENT_ENABLED_STATE_ENABLED, PackageManager.DONT_KILL_APP);
        } catch (IllegalArgumentException noSuchIcon) {
            return;
        }
        pm.setComponentEnabledSetting(new ComponentName(this, getPackageName() + "." + shown),
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED, PackageManager.DONT_KILL_APP);
        prefs.edit().putString(KEY_ICON_SHOWN, wanted).apply();
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        if (web != null) web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web == null) {
            moveTaskToBack(true);
            return;
        }
        // The page closes its own sheets, settings and sidebar first.
        web.evaluateJavascript("window.violaBack ? window.violaBack() : false", handled -> {
            if ("true".equals(handled)) return;
            if (web.canGoBack()) web.goBack();
            else moveTaskToBack(true);
        });
    }
}
