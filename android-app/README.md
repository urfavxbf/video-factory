# Video Factory Android MVP

This is the native Android app project, written in Kotlin and Jetpack Compose.

## Current MVP
- Topic input
- Local content pack generation (title, narration script, caption, hashtags)
- Android Text-to-Speech playback
- Copy buttons for each text field
- Vertical 9:16-style preview mockup

## Build an APK without a computer
The repository workflow `.github/workflows/build-android.yml` builds the debug APK in GitHub Actions.

1. Open the repository's **Actions** tab.
2. Select **Build Video Factory Android APK**.
3. Tap **Run workflow** and confirm.
4. Open the completed run and download the `VideoFactory-debug-apk` artifact.
5. Extract the ZIP on your phone and install `app-debug.apk`. Android may ask you to allow installs from your browser or file manager.

## Planned next milestone
Implement actual MP4 rendering/export, timed subtitles, and a real video player preview. The current preview is a mockup and does not yet export an MP4.
