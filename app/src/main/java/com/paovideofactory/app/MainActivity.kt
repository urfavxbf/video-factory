package com.paovideofactory.app

import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import android.content.ContentValues
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Color as AndroidColor
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.view.Surface
import java.io.File
import java.io.FileInputStream
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

class MainActivity : ComponentActivity() {
    private var tts: TextToSpeech? = null
    private var ttsReady = false

    private fun exportVideo(title: String, script: String, onStatus: (String) -> Unit) {
        Thread {
            try {
                onStatus("Gumagawa ng MP4... huwag munang isara ang app.")
                val width = 360
                val height = 640
                val fps = 15
                val durationSeconds = 12
                val output = File(cacheDir, "video-factory-${System.currentTimeMillis()}.mp4")
                val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height).apply {
                    setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
                    setInteger(MediaFormat.KEY_BIT_RATE, 1_200_000)
                    setInteger(MediaFormat.KEY_FRAME_RATE, fps)
                    setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
                }
                val encoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
                encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
                val surface = encoder.createInputSurface()
                val muxer = MediaMuxer(output.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
                encoder.start()
                val info = MediaCodec.BufferInfo()
                var track = -1
                var muxerStarted = false
                val paint = Paint(Paint.ANTI_ALIAS_FLAG)
                val lines = script.chunked(34).take(8)
                for (frame in 0 until fps * durationSeconds) {
                    val canvas: Canvas = surface.lockCanvas(null)
                    try {
                        val progress = frame.toFloat() / (fps * durationSeconds)
                        canvas.drawColor(AndroidColor.rgb((10 + progress * 25).toInt(), 17, 42))
                        paint.color = AndroidColor.rgb(30, 65, 105)
                        canvas.drawCircle(width * (0.25f + progress * 0.5f), height * 0.32f, 110f, paint)
                        paint.color = AndroidColor.rgb(114, 242, 195)
                        paint.textAlign = Paint.Align.CENTER
                        paint.typeface = android.graphics.Typeface.create("sans-serif-black", android.graphics.Typeface.BOLD)
                        paint.textSize = 20f
                        canvas.drawText("ALAM MO BA?", width / 2f, 100f, paint)
                        paint.color = AndroidColor.WHITE
                        paint.textSize = 25f
                        val titleLines = title.chunked(22).take(4)
                        titleLines.forEachIndexed { i, line -> canvas.drawText(line, width / 2f, 180f + i * 34f, paint) }
                        paint.color = AndroidColor.rgb(114, 242, 195)
                        paint.textSize = 15f
                        val lineIndex = ((frame / (fps * 1.5f)).toInt()).coerceIn(0, (lines.size - 1).coerceAtLeast(0))
                        val caption = lines.getOrElse(lineIndex) { "Sundan para sa mas marami pang facts!" }
                        paint.color = AndroidColor.argb(220, 0, 0, 0)
                        canvas.drawRoundRect(18f, height - 150f, width - 18f, height - 65f, 14f, 14f, paint)
                        paint.color = AndroidColor.WHITE
                        paint.textSize = 17f
                        canvas.drawText(caption, width / 2f, height - 105f, paint)
                        paint.color = AndroidColor.rgb(114, 242, 195)
                        paint.textSize = 12f
                        canvas.drawText("VIDEO FACTORY • 9:16", width / 2f, height - 30f, paint)
                    } finally { surface.unlockCanvasAndPost(canvas) }
                    val bufferInfo = MediaCodec.BufferInfo()
                    var outputIndex = encoder.dequeueOutputBuffer(bufferInfo, 0)
                    while (outputIndex != MediaCodec.INFO_TRY_AGAIN_LATER) {
                        when {
                            outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                                if (!muxerStarted) {
                                    track = muxer.addTrack(encoder.outputFormat)
                                    muxer.start()
                                    muxerStarted = true
                                }
                            }
                            outputIndex >= 0 -> {
                                val encoded = encoder.getOutputBuffer(outputIndex)
                                if (encoded != null && bufferInfo.size > 0 && muxerStarted) {
                                    encoded.position(bufferInfo.offset)
                                    encoded.limit(bufferInfo.offset + bufferInfo.size)
                                    muxer.writeSampleData(track, encoded, bufferInfo)
                                }
                                encoder.releaseOutputBuffer(outputIndex, false)
                            }
                        }
                        outputIndex = encoder.dequeueOutputBuffer(bufferInfo, 0)
                    }
                    Thread.sleep(1000L / fps)
                }
                encoder.signalEndOfInputStream()
                var finished = false
                while (!finished) {
                    val index = encoder.dequeueOutputBuffer(info, 10_000)
                    when {
                        index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                            if (!muxerStarted) {
                                track = muxer.addTrack(encoder.outputFormat)
                                muxer.start()
                                muxerStarted = true
                            }
                        }
                        index >= 0 -> {
                            val data = encoder.getOutputBuffer(index)
                            if (data != null && info.size > 0 && muxerStarted) {
                                data.position(info.offset)
                                data.limit(info.offset + info.size)
                                muxer.writeSampleData(track, data, info)
                            }
                            if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) finished = true
                            encoder.releaseOutputBuffer(index, false)
                        }
                    }
                }
                encoder.stop(); encoder.release(); surface.release()
                if (muxerStarted) muxer.stop()
                muxer.release()
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, "VideoFactory-${System.currentTimeMillis()}.mp4")
                    put(MediaStore.MediaColumns.MIME_TYPE, "video/mp4")
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_MOVIES + "/VideoFactory")
                }
                val uri = contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values) ?: error("Hindi makagawa ng save location.")
                contentResolver.openOutputStream(uri)?.use { out -> FileInputStream(output).use { input -> input.copyTo(out) } } ?: error("Hindi maisulat ang MP4.")
                output.delete()
                runOnUiThread { onStatus("Tapos na! Nasa Movies/VideoFactory ang MP4 mo. (Walang narration audio sa unang version.)") }
            } catch (e: Exception) {
                runOnUiThread { onStatus("Hindi nagawa ang MP4: ${e.message ?: "unknown error"}") }
            }
        }.start()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tts = TextToSpeech(this) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) tts?.language = Locale("fil", "PH")
        }
        setContent { VideoFactoryScreen(onSpeak = { text ->
            if (ttsReady) tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "vf-narration")
            else Toast.makeText(this, "Hindi pa handa ang Text-to-Speech sa device.", Toast.LENGTH_LONG).show()
        }, onExport = { title, script, onStatus -> exportVideo(title, script, onStatus) }) }
    }

    override fun onDestroy() {
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }
}

private data class VideoPack(val title: String, val script: String, val caption: String, val tags: String)

private fun makePack(topic: String): VideoPack {
    val clean = topic.trim().ifBlank { "kamangha-manghang science facts" }
    val title = "ALAM MO BA? $clean"
    val script = "Alam mo ba? Ngayon, pag-uusapan natin ang $clean. " +
        "Maraming bagay sa mundo ang nakakagulat kapag mas inalam natin ang dahilan sa likod nito. " +
        "Isipin mo ito: bawat bagong kaalaman ay puwedeng magbago sa paraan ng pagtingin natin sa paligid. " +
        "Kaya kung mahilig ka sa facts, science, at mga kuwentong nakakagulat, sundan ang page para sa mas marami pang videos. " +
        "I-comment ang susunod na topic na gusto mong malaman!"
    val caption = "May alam ka na ba tungkol sa $clean? 🤯 Panoorin hanggang dulo at sabihin sa comments ang susunod na topic!"
    val tags = "#AlamMoBa #ScienceFacts #FilipinoFacts #LearnOnTikTok #YouTubeShorts"
    return VideoPack(title, script, caption, tags)
}

@Composable
private fun VideoFactoryScreen(onSpeak: (String) -> Unit, onExport: (String, String, (String) -> Unit) -> Unit) {
    val context = LocalContext.current
    var topic by remember { mutableStateOf("mga misteryo ng kalawakan") }
    var pack by remember { mutableStateOf(makePack(topic)) }
    var notice by remember { mutableStateOf("Ilagay ang topic at pindutin ang Generate Pack.") }
    var exporting by remember { mutableStateOf(false) }
    val bg = Color(0xFF0A0F1E)
    val panel = Color(0xFF151D31)
    val accent = Color(0xFF72F2C3)

    MaterialTheme(colorScheme = darkColorScheme(primary = accent, background = bg, surface = panel)) {
        Column(
            modifier = Modifier.fillMaxSize().background(bg).verticalScroll(rememberScrollState()).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Box(
                    modifier = Modifier.size(48.dp).background(
                        Brush.linearGradient(listOf(accent, Color(0xFF5B8CFF))), RoundedCornerShape(14.dp)
                    ),
                    contentAlignment = Alignment.Center
                ) { Text("VF", color = bg, fontWeight = FontWeight.Black, fontSize = 20.sp) }
                Column {
                    Text("VIDEO FACTORY", color = Color.White, fontWeight = FontWeight.Black, fontSize = 22.sp)
                    Text("Shorts Studio • Filipino edition", color = Color.LightGray, fontSize = 12.sp)
                }
            }

            Card(colors = CardDefaults.cardColors(containerColor = panel), shape = RoundedCornerShape(20.dp)) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("01 / VIDEO TOPIC", color = accent, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    OutlinedTextField(
                        value = topic, onValueChange = { topic = it }, label = { Text("Anong topic ng video?") },
                        modifier = Modifier.fillMaxWidth(), minLines = 2
                    )
                    Button(
                        onClick = { pack = makePack(topic); notice = "Nagawa ang title, script, caption at hashtags." },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("✦  GENERATE CONTENT PACK") }
                }
            }

            Button(onClick = { exporting = true; onExport(pack.title, pack.script) { message -> notice = message; exporting = message.startsWith("Gumagawa") } }, modifier = Modifier.fillMaxWidth(), enabled = !exporting) { Text(if (exporting) "GENERATING MP4..." else "⬇  GENERATE & SAVE MP4") }

            // Vertical preview of the generated video.
            Box(
                modifier = Modifier.fillMaxWidth().height(320.dp).background(
                    Brush.linearGradient(listOf(Color(0xFF142D4D), Color(0xFF29184A), Color(0xFF071018))),
                    RoundedCornerShape(22.dp)
                ).padding(22.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    Text("ALAM MO BA?", color = accent, fontWeight = FontWeight.Black, fontSize = 16.sp)
                    Text(pack.title.removePrefix("ALAM MO BA? "), color = Color.White, fontWeight = FontWeight.Black, fontSize = 27.sp, lineHeight = 32.sp)
                    Text("FACTS • KNOWLEDGE • CURIOSITY", color = Color.LightGray, fontSize = 10.sp)
                    Text("9:16 PREVIEW", color = accent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }

            ContentCard("VIDEO TITLE", pack.title, panel) { copyText(context, "Title", pack.title) }
            ContentCard("NARRATION SCRIPT", pack.script, panel) {
                copyText(context, "Script", pack.script)
                onSpeak(pack.script)
            }
            ContentCard("CAPTION", pack.caption, panel) { copyText(context, "Caption", pack.caption) }
            ContentCard("HASHTAGS", pack.tags, panel) { copyText(context, "Hashtags", pack.tags) }

            Text(notice, color = accent, fontSize = 12.sp)
            Text(
                "MP4 export creates a 12-second animated vertical video. Narration audio is not included yet.",
                color = Color.Gray, fontSize = 11.sp
            )
            Spacer(Modifier.height(12.dp))
        }
    }
}

@Composable
private fun ContentCard(title: String, value: String, panel: Color, onCopy: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = panel), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, color = Color(0xFF72F2C3), fontWeight = FontWeight.Bold, fontSize = 11.sp)
            Text(value, color = Color.White, fontSize = 14.sp, lineHeight = 21.sp)
            OutlinedButton(onClick = onCopy) { Text(if (title == "NARRATION SCRIPT") "COPY SCRIPT + SPEAK" else "COPY") }
        }
    }
}

private fun copyText(context: Context, label: String, text: String) {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    clipboard.setPrimaryClip(ClipData.newPlainText(label, text))
    Toast.makeText(context, "$label copied!", Toast.LENGTH_SHORT).show()
}
