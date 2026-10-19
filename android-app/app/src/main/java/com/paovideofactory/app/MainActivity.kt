package com.paovideofactory.app

import android.os.Bundle

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Color as AndroidColor
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.content.ContentValues
import android.os.Environment
import android.provider.MediaStore
import java.nio.ByteBuffer
import java.text.SimpleDateFormat
import java.util.Date
import android.speech.tts.TextToSpeech
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tts = TextToSpeech(this) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) tts?.language = Locale("fil", "PH")
        }
        setContent { VideoFactoryScreen(
            onSpeak = { text ->
                if (ttsReady) tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "vf-narration")
                else Toast.makeText(this, "Hindi pa handa ang Text-to-Speech sa device.", Toast.LENGTH_LONG).show()
            },
            onGenerateVideo = { title ->
                Toast.makeText(this, "Ginagawa ang MP4. Huwag munang isara ang app.", Toast.LENGTH_LONG).show()
                Thread {
                    try {
                        renderVideoToGallery(this, title)
                        runOnUiThread { Toast.makeText(this, "Tapos na! Nasa Movies/Video Factory ang MP4.", Toast.LENGTH_LONG).show() }
                    } catch (e: Exception) {
                        runOnUiThread { Toast.makeText(this, "Hindi nagawa ang video: ${e.message ?: "encoding error"}", Toast.LENGTH_LONG).show() }
                    }
                }.start()
            }
        ) }
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
private fun VideoFactoryScreen(onSpeak: (String) -> Unit, onGenerateVideo: (String) -> Unit) {
    val context = LocalContext.current
    var topic by remember { mutableStateOf("mga misteryo ng kalawakan") }
    var pack by remember { mutableStateOf(makePack(topic)) }
    var notice by remember { mutableStateOf("Ilagay ang topic at pindutin ang Generate Pack.") }
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

            // Vertical preview for the generated short.
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

            Button(
                onClick = { onGenerateVideo(pack.title) },
                modifier = Modifier.fillMaxWidth()
            ) { Text("▶  GENERATE & SAVE MP4") }

            ContentCard("VIDEO TITLE", pack.title, panel) { copyText(context, "Title", pack.title) }
            ContentCard("NARRATION SCRIPT", pack.script, panel) {
                copyText(context, "Script", pack.script)
                onSpeak(pack.script)
            }
            ContentCard("CAPTION", pack.caption, panel) { copyText(context, "Caption", pack.caption) }
            ContentCard("HASHTAGS", pack.tags, panel) { copyText(context, "Hashtags", pack.tags) }

            Text(notice, color = accent, fontSize = 12.sp)
            Text(
                "MVP 0.2 • Content pack + TTS preview + on-device MP4 export.",
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


/**
 * Renders a simple vertical animated text video entirely on the device using
 * Android MediaCodec + MediaMuxer. This first version exports silent video;
 * narration audio muxing is the next milestone.
 */
private fun renderVideoToGallery(context: Context, title: String) {
    val width = 360
    val height = 640
    val fps = 15
    val durationSeconds = 12
    val frameCount = fps * durationSeconds
    val mime = "video/avc"
    val values = ContentValues().apply {
        put(MediaStore.Video.Media.DISPLAY_NAME, "VideoFactory_${System.currentTimeMillis()}.mp4")
        put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
        put(MediaStore.Video.Media.RELATIVE_PATH, Environment.DIRECTORY_MOVIES + "/Video Factory")
        put(MediaStore.Video.Media.IS_PENDING, 1)
    }
    val resolver = context.contentResolver
    val uri = resolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values)
        ?: throw IllegalStateException("Hindi makagawa ng output file.")
    var codec: MediaCodec? = null
    var muxer: MediaMuxer? = null
    var outputDescriptor: android.os.ParcelFileDescriptor? = null
    var muxerStarted = false
    var trackIndex = -1
    try {
        outputDescriptor = resolver.openFileDescriptor(uri, "rw")
            ?: throw IllegalStateException("Hindi mabuksan ang output file.")
        run {
            codec = MediaCodec.createEncoderByType(mime)
            val format = MediaFormat.createVideoFormat(mime, width, height).apply {
                setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar)
                setInteger(MediaFormat.KEY_BIT_RATE, 1_000_000)
                setInteger(MediaFormat.KEY_FRAME_RATE, fps)
                setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
            }
            codec!!.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            codec!!.start()
            muxer = MediaMuxer(outputDescriptor!!.fileDescriptor, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val info = MediaCodec.BufferInfo()
            var frameIndex = 0
            var inputDone = false
            var outputDone = false
            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bitmap)
            val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { textAlign = Paint.Align.CENTER }
            val cleanTitle = title.removePrefix("ALAM MO BA? ").ifBlank { "Kamangha-manghang facts" }
            while (!outputDone) {
                if (!inputDone) {
                    val inputIndex = codec!!.dequeueInputBuffer(10_000)
                    if (inputIndex >= 0) {
                        val input = codec!!.getInputBuffer(inputIndex)
                            ?: throw IllegalStateException("Walang encoder input buffer.")
                        if (frameIndex >= frameCount) {
                            codec!!.queueInputBuffer(inputIndex, 0, 0, frameIndex.toLong() * 1_000_000L / fps, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            inputDone = true
                        } else {
                            drawVideoFrame(canvas, paint, width, height, cleanTitle, frameIndex, frameCount)
                            val yuv = bitmapToNv12(bitmap)
                            input.clear()
                            input.put(yuv)
                            codec!!.queueInputBuffer(inputIndex, 0, yuv.size, frameIndex.toLong() * 1_000_000L / fps, 0)
                            frameIndex++
                        }
                    }
                }
                val outputIndex = codec!!.dequeueOutputBuffer(info, 10_000)
                when {
                    outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                        trackIndex = muxer!!.addTrack(codec!!.outputFormat)
                        muxer!!.start()
                        muxerStarted = true
                    }
                    outputIndex >= 0 -> {
                        val output = codec!!.getOutputBuffer(outputIndex)
                        if (output != null && info.size > 0 && muxerStarted) {
                            output.position(info.offset)
                            output.limit(info.offset + info.size)
                            muxer!!.writeSampleData(trackIndex, output, info)
                        }
                        val end = (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0
                        codec!!.releaseOutputBuffer(outputIndex, false)
                        if (end) outputDone = true
                    }
                }
            }
            bitmap.recycle()
        }
        resolver.update(uri, ContentValues().apply { put(MediaStore.Video.Media.IS_PENDING, 0) }, null, null)
    } catch (e: Exception) {
        resolver.delete(uri, null, null)
        throw e
    } finally {
        try { codec?.stop() } catch (_: Exception) {}
        try { codec?.release() } catch (_: Exception) {}
        try { if (muxerStarted) muxer?.stop() } catch (_: Exception) {}
        try { muxer?.release() } catch (_: Exception) {}
        try { outputDescriptor?.close() } catch (_: Exception) {}
    }
}

private fun drawVideoFrame(
    canvas: Canvas,
    paint: Paint,
    width: Int,
    height: Int,
    title: String,
    frame: Int,
    totalFrames: Int
) {
    val phase = frame.toFloat() / totalFrames
    val top = AndroidColor.rgb((16 + 22 * phase).toInt(), (35 + 12 * phase).toInt(), 75)
    canvas.drawColor(top)
    paint.color = AndroidColor.rgb(114, 242, 195)
    paint.textSize = 24f
    paint.typeface = android.graphics.Typeface.create("sans-serif-black", android.graphics.Typeface.BOLD)
    canvas.drawText("ALAM MO BA?", width / 2f, 145f, paint)
    paint.color = AndroidColor.WHITE
    paint.textSize = 30f
    val words = title.split(" ")
    val lines = mutableListOf<String>()
    var line = ""
    for (word in words) {
        val candidate = if (line.isEmpty()) word else "$line $word"
        if (paint.measureText(candidate) > width - 48 && line.isNotEmpty()) {
            lines.add(line)
            line = word
        } else line = candidate
    }
    if (line.isNotEmpty()) lines.add(line)
    val visibleLines = lines.take(7)
    val startY = height / 2f - (visibleLines.size - 1) * 20f
    visibleLines.forEachIndexed { index, text ->
        canvas.drawText(text, width / 2f, startY + index * 42f, paint)
    }
    paint.color = AndroidColor.LTGRAY
    paint.textSize = 13f
    paint.typeface = android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.NORMAL)
    canvas.drawText("FACTS • KNOWLEDGE • CURIOSITY", width / 2f, height - 70f, paint)
    paint.color = AndroidColor.rgb(114, 242, 195)
    canvas.drawRect(24f, height - 35f, 24f + (width - 48f) * phase, height - 29f, paint)
}

private fun bitmapToNv12(bitmap: Bitmap): ByteArray {
    val width = bitmap.width
    val height = bitmap.height
    val argb = IntArray(width * height)
    bitmap.getPixels(argb, 0, width, 0, 0, width, height)
    val output = ByteArray(width * height * 3 / 2)
    var yIndex = 0
    var uvIndex = width * height
    for (row in 0 until height) {
        for (col in 0 until width) {
            val pixel = argb[row * width + col]
            val r = (pixel shr 16) and 0xff
            val g = (pixel shr 8) and 0xff
            val b = pixel and 0xff
            val y = ((66 * r + 129 * g + 25 * b + 128) shr 8) + 16
            output[yIndex++] = y.coerceIn(0, 255).toByte()
            if (row % 2 == 0 && col % 2 == 0) {
                val u = ((-38 * r - 74 * g + 112 * b + 128) shr 8) + 128
                val v = ((112 * r - 94 * g - 18 * b + 128) shr 8) + 128
                output[uvIndex++] = u.coerceIn(0, 255).toByte()
                output[uvIndex++] = v.coerceIn(0, 255).toByte()
            }
        }
    }
    return output
}
