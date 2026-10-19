package com.paovideofactory.app

import android.content.ContentValues
import android.content.Context
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.view.Surface
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Shader
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * Fully on-device MP4 exporter: Android TTS -> PCM WAV -> AAC, animated AVC video,
 * then muxes both tracks into one MP4 and saves it through MediaStore.
 */
object NativeVideoExporter {
    private const val WIDTH = 360
    private const val HEIGHT = 640
    private const val FPS = 15
    private const val DURATION_SECONDS = 45
    private const val FRAME_COUNT = FPS * DURATION_SECONDS

    fun export(context: Context, title: String, script: String, progress: (String) -> Unit): Uri {
        val workDir = File(context.cacheDir, "vf_export").apply {
            if (exists()) listFiles()?.forEach { it.delete() }
            mkdirs()
        }
        val wav = File(workDir, "narration.wav")
        val audioMp4 = File(workDir, "audio.m4a")
        val videoMp4 = File(workDir, "video.mp4")
        val finalMp4 = File(workDir, "final.mp4")
        try {
            progress("1/4 • Gumagawa ng Filipino narration…")
            synthesize(context, script, wav)
            progress("2/4 • Inihahanda ang audio…")
            encodeWavToAac(wav, audioMp4)
            progress("3/4 • Nirender ang 45-second vertical video…")
            encodeVideo(title, script, videoMp4, progress)
            progress("4/4 • Pinag-iisa ang audio at video…")
            muxTracks(videoMp4, audioMp4, finalMp4)
            progress("Sine-save ang MP4 sa Movies/VideoFactory…")
            return saveToMovies(context, finalMp4, title)
        } finally {
            workDir.listFiles()?.forEach { it.delete() }
        }
    }

    private fun synthesize(context: Context, script: String, output: File) {
        val ready = CountDownLatch(1)
        val finished = CountDownLatch(1)
        var tts: TextToSpeech? = null
        var initStatus = TextToSpeech.ERROR
        var synthesisError: String? = null
        try {
            tts = TextToSpeech(context.applicationContext) { status ->
                initStatus = status
                ready.countDown()
            }
            check(ready.await(20, TimeUnit.SECONDS)) { "Nag-timeout ang Text-to-Speech initialization." }
            check(initStatus == TextToSpeech.SUCCESS) {
                "Hindi available ang Android Text-to-Speech. I-install o i-enable ang TTS engine sa Settings."
            }
            val engine = tts ?: error("Hindi na-initialize ang Text-to-Speech.")
            val languageResult = engine.setLanguage(Locale("fil", "PH"))
            if (languageResult == TextToSpeech.LANG_MISSING_DATA ||
                languageResult == TextToSpeech.LANG_NOT_SUPPORTED) {
                val fallback = engine.setLanguage(Locale("en", "US"))
                check(fallback != TextToSpeech.LANG_MISSING_DATA &&
                    fallback != TextToSpeech.LANG_NOT_SUPPORTED) {
                    "Walang suportadong TTS voice sa device."
                }
            }
            engine.setSpeechRate(0.92f)
            engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) = Unit
                override fun onDone(utteranceId: String?) { finished.countDown() }
                @Deprecated("Deprecated in Android API")
                override fun onError(utteranceId: String?) {
                    synthesisError = "Nag-error ang pagbuo ng narration."
                    finished.countDown()
                }
                override fun onError(utteranceId: String?, errorCode: Int) {
                    synthesisError = "Nag-error ang pagbuo ng narration (code " + errorCode + ")."
                    finished.countDown()
                }
            })
            output.delete()
            val result = engine.synthesizeToFile(script, Bundle(), output, "vf-narration-export")
            check(result == TextToSpeech.SUCCESS) { "Hindi masimulan ang narration synthesis." }
            check(finished.await(120, TimeUnit.SECONDS)) { "Nag-timeout ang narration generation." }
            check(synthesisError == null) { synthesisError ?: "Hindi nagawa ang narration." }
            check(output.exists() && output.length() > 44L) { "Walang audio file na nalikha ng TTS." }
        } finally {
            tts?.stop()
            tts?.shutdown()
        }
    }

    private data class WavData(val sampleRate: Int, val channels: Int, val pcm: ByteArray)

    private fun readWav(file: File): WavData {
        val bytes = file.readBytes()
        check(bytes.size > 44) { "Walang laman ang narration WAV." }
        val header = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        check(String(bytes, 0, 4, Charsets.US_ASCII) == "RIFF" &&
            String(bytes, 8, 4, Charsets.US_ASCII) == "WAVE") {
            "Hindi valid na WAV file ang narration output."
        }
        var pos = 12
        var sampleRate = 0
        var channels = 0
        var dataOffset = -1
        var dataSize = 0
        while (pos + 8 <= bytes.size) {
            val id = String(bytes, pos, 4, Charsets.US_ASCII)
            val size = ByteBuffer.wrap(bytes, pos + 4, 4).order(ByteOrder.LITTLE_ENDIAN).int
            val start = pos + 8
            if (size < 0 || start + size > bytes.size) break
            if (id == "fmt " && size >= 16) {
                val fmt = ByteBuffer.wrap(bytes, start, size).order(ByteOrder.LITTLE_ENDIAN)
                val audioFormat = fmt.short.toInt() and 0xffff
                channels = fmt.short.toInt() and 0xffff
                sampleRate = fmt.int
                fmt.int
                fmt.short
                val bits = fmt.short.toInt() and 0xffff
                check(audioFormat == 1 && bits == 16) { "16-bit PCM WAV ang kailangan para sa narration." }
            } else if (id == "data") {
                dataOffset = start
                dataSize = size
                break
            }
            pos = start + size + (size and 1)
        }
        check(sampleRate > 0 && channels in 1..2 && dataOffset >= 0) { "Hindi mabasa ang WAV audio format." }
        val safeSize = min(dataSize, bytes.size - dataOffset)
        return WavData(sampleRate, channels, bytes.copyOfRange(dataOffset, dataOffset + safeSize))
    }

    private fun encodeWavToAac(wavFile: File, outputFile: File) {
        val wav = readWav(wavFile)
        val format = MediaFormat.createAudioFormat("audio/mp4a-latm", wav.sampleRate, wav.channels).apply {
            setInteger(MediaFormat.KEY_AAC_PROFILE, android.media.MediaCodecInfo.CodecProfileLevel.AACObjectLC)
            setInteger(MediaFormat.KEY_BIT_RATE, 96000)
            setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16384)
        }
        val encoder = MediaCodec.createEncoderByType("audio/mp4a-latm")
        val muxer = MediaMuxer(outputFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var track = -1
        var muxerStarted = false
        var inputOffset = 0
        var inputDone = false
        var outputDone = false
        val info = MediaCodec.BufferInfo()
        try {
            encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            encoder.start()
            while (!outputDone) {
                if (!inputDone) {
                    val inputIndex = encoder.dequeueInputBuffer(10000)
                    if (inputIndex >= 0) {
                        val input = encoder.getInputBuffer(inputIndex)!!
                        input.clear()
                        val remaining = wav.pcm.size - inputOffset
                        if (remaining <= 0) {
                            val pts = (inputOffset.toLong() * 1000000L) /
                                (wav.sampleRate.toLong() * wav.channels * 2L)
                            encoder.queueInputBuffer(inputIndex, 0, 0, pts, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            inputDone = true
                        } else {
                            var count = min(input.remaining(), remaining)
                            val frameBytes = wav.channels * 2
                            count -= count % frameBytes
                            if (count == 0) count = min(remaining, frameBytes)
                            input.put(wav.pcm, inputOffset, count)
                            val pts = (inputOffset.toLong() * 1000000L) /
                                (wav.sampleRate.toLong() * wav.channels * 2L)
                            encoder.queueInputBuffer(inputIndex, 0, count, pts, 0)
                            inputOffset += count
                        }
                    }
                }
                val outputIndex = encoder.dequeueOutputBuffer(info, 10000)
                when {
                    outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                        track = muxer.addTrack(encoder.outputFormat)
                        muxer.start()
                        muxerStarted = true
                    }
                    outputIndex >= 0 -> {
                        val buffer = encoder.getOutputBuffer(outputIndex)
                        if (info.size > 0 && buffer != null && muxerStarted) {
                            buffer.position(info.offset)
                            buffer.limit(info.offset + info.size)
                            muxer.writeSampleData(track, buffer, info)
                        }
                        if ((info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outputDone = true
                        encoder.releaseOutputBuffer(outputIndex, false)
                    }
                }
            }
            check(muxerStarted) { "Hindi nagawa ang AAC audio track." }
        } finally {
            try { encoder.stop() } catch (_: Exception) {}
            encoder.release()
            if (muxerStarted) try { muxer.stop() } catch (_: Exception) {}
            muxer.release()
        }
    }

    private fun encodeVideo(title: String, script: String, output: File, progress: (String) -> Unit) {
        val format = MediaFormat.createVideoFormat("video/avc", WIDTH, HEIGHT).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT, android.media.MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
            setInteger(MediaFormat.KEY_BIT_RATE, 1_600_000)
            setInteger(MediaFormat.KEY_FRAME_RATE, FPS)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
        }
        val encoder = MediaCodec.createEncoderByType("video/avc")
        val muxer = MediaMuxer(output.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var surface: Surface? = null
        var track = -1
        var muxerStarted = false
        var outputDone = false
        val info = MediaCodec.BufferInfo()
        try {
            encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            surface = encoder.createInputSurface()
            encoder.start()
            val captions = script.split(Regex("(?<=[.!?])\\s+")).filter { it.isNotBlank() }
            val paint = Paint(Paint.ANTI_ALIAS_FLAG)
            for (frame in 0 until FRAME_COUNT) {
                val canvas = surface.lockCanvas(null)
                try {
                    drawFrame(canvas, frame, title, captions, paint)
                } finally {
                    surface.unlockCanvasAndPost(canvas)
                }
                drainVideoEncoder(encoder, muxer, info) { newTrack ->
                    track = newTrack
                    muxerStarted = true
                }
                if (frame % FPS == 0) {
                    progress("3/4 • Video rendering: " + (frame * 100 / FRAME_COUNT) + "%")
                }
                Thread.sleep(66L)
            }
            encoder.signalEndOfInputStream()
            while (!outputDone) {
                val result = drainVideoEncoder(encoder, muxer, info) { newTrack ->
                    track = newTrack
                    muxerStarted = true
                }
                outputDone = result
            }
            check(track >= 0 && muxerStarted) { "Hindi nagawa ang video track." }
        } finally {
            try { surface?.release() } catch (_: Exception) {}
            try { encoder.stop() } catch (_: Exception) {}
            encoder.release()
            if (muxerStarted) try { muxer.stop() } catch (_: Exception) {}
            muxer.release()
        }
    }

    private fun drainVideoEncoder(
        encoder: MediaCodec,
        muxer: MediaMuxer,
        info: MediaCodec.BufferInfo,
        onTrack: (Int) -> Unit
    ): Boolean {
        var eos = false
        while (true) {
            val index = encoder.dequeueOutputBuffer(info, 0)
            when {
                index == MediaCodec.INFO_TRY_AGAIN_LATER -> return eos
                index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    val track = muxer.addTrack(encoder.outputFormat)
                    muxer.start()
                    onTrack(track)
                }
                index >= 0 -> {
                    val buffer = encoder.getOutputBuffer(index)
                    if (info.size > 0 && buffer != null) {
                        buffer.position(info.offset)
                        buffer.limit(info.offset + info.size)
                        muxer.writeSampleData(0, buffer, info)
                    }
                    if ((info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) eos = true
                    encoder.releaseOutputBuffer(index, false)
                    if (eos) return true
                }
            }
        }
    }

    private fun drawFrame(canvas: Canvas, frame: Int, title: String, captions: List<String>, paint: Paint) {
        val t = frame.toFloat() / FPS
        val shift = ((sin(t * 0.42) + 1.0) * 0.5).toFloat()
        paint.shader = LinearGradient(
            0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(),
            intArrayOf(Color.rgb(8, 20, 43), Color.rgb(28 + (shift * 18).toInt(), 20, 62), Color.rgb(5, 13, 25)),
            null, Shader.TileMode.CLAMP
        )
        canvas.drawRect(0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(), paint)
        paint.shader = null
        paint.color = Color.argb(35, 100, 245, 205)
        canvas.drawCircle(300f + sin(t * 0.7).toFloat() * 32f, 125f + sin(t * 0.4).toFloat() * 45f, 85f, paint)
        canvas.drawCircle(42f + sin(t * 0.3).toFloat() * 22f, 490f + sin(t * 0.6).toFloat() * 25f, 110f, paint)

        paint.color = Color.rgb(114, 242, 195)
        paint.textSize = 16f
        paint.typeface = android.graphics.Typeface.create("sans-serif-black", android.graphics.Typeface.BOLD)
        canvas.drawText("VIDEO FACTORY • ALAM MO BA?", 22f, 48f, paint)

        paint.color = Color.WHITE
        paint.textSize = 28f
        val titleLines = wrapText(title.uppercase(Locale.getDefault()), paint, 310f).take(4)
        var y = 145f
        for (line in titleLines) {
            canvas.drawText(line, 24f, y, paint)
            y += 36f
        }

        val captionIndex = if (captions.isEmpty()) 0 else min(captions.size - 1, (t / DURATION_SECONDS * captions.size).toInt())
        val caption = captions.getOrElse(captionIndex) { title }
        paint.color = Color.BLACK
        canvas.drawRoundRect(15f, 430f, 345f, 570f, 18f, 18f, paint)
        paint.color = Color.rgb(114, 242, 195)
        paint.textSize = 12f
        paint.typeface = android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.BOLD)
        canvas.drawText("PANOORIN AT ALAMIN", 30f, 454f, paint)
        paint.color = Color.WHITE
        paint.textSize = 19f
        paint.typeface = android.graphics.Typeface.create("sans-serif-medium", android.graphics.Typeface.NORMAL)
        val lines = wrapText(caption, paint, 292f).take(4)
        y = 483f
        for (line in lines) {
            canvas.drawText(line, 30f, y, paint)
            y += 22f
        }
        paint.color = Color.rgb(114, 242, 195)
        paint.textSize = 11f
        canvas.drawText("FOLLOW PARA SA MAS MARAMING FACTS", 22f, 610f, paint)
    }

    private fun wrapText(text: String, paint: Paint, maxWidth: Float): List<String> {
        val result = mutableListOf<String>()
        var line = ""
        for (word in text.split(Regex("\\s+"))) {
            val candidate = if (line.isEmpty()) word else line + " " + word
            if (paint.measureText(candidate) > maxWidth && line.isNotEmpty()) {
                result.add(line)
                line = word
            } else line = candidate
        }
        if (line.isNotEmpty()) result.add(line)
        return result
    }

    private fun muxTracks(videoFile: File, audioFile: File, outputFile: File) {
        val video = MediaExtractor()
        val audio = MediaExtractor()
        val muxer = MediaMuxer(outputFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var started = false
        try {
            video.setDataSource(videoFile.absolutePath)
            audio.setDataSource(audioFile.absolutePath)
            var videoTrackIn = -1
            var audioTrackIn = -1
            for (i in 0 until video.trackCount) {
                val f = video.getTrackFormat(i)
                if (f.getString(MediaFormat.KEY_MIME)?.startsWith("video/") == true) {
                    videoTrackIn = i
                    muxer.addTrack(f)
                    break
                }
            }
            for (i in 0 until audio.trackCount) {
                val f = audio.getTrackFormat(i)
                if (f.getString(MediaFormat.KEY_MIME)?.startsWith("audio/") == true) {
                    audioTrackIn = i
                    muxer.addTrack(f)
                    break
                }
            }
            check(videoTrackIn >= 0 && audioTrackIn >= 0) { "Hindi makita ang video o audio track." }
            val videoTrackOut = 0
            val audioTrackOut = 1
            muxer.start()
            started = true
            copySamples(video, videoTrackIn, videoTrackOut, muxer)
            copySamples(audio, audioTrackIn, audioTrackOut, muxer)
        } finally {
            video.release()
            audio.release()
            if (started) try { muxer.stop() } catch (_: Exception) {}
            muxer.release()
        }
    }

    private fun copySamples(extractor: MediaExtractor, inputTrack: Int, outputTrack: Int, muxer: MediaMuxer) {
        extractor.selectTrack(inputTrack)
        val buffer = ByteBuffer.allocate(1024 * 1024)
        val info = MediaCodec.BufferInfo()
        while (true) {
            buffer.clear()
            val size = extractor.readSampleData(buffer, 0)
            if (size < 0) break
            info.offset = 0
            info.size = size
            info.presentationTimeUs = extractor.sampleTime
            info.flags = extractor.sampleFlags
            muxer.writeSampleData(outputTrack, buffer, info)
            extractor.advance()
        }
        extractor.unselectTrack(inputTrack)
    }

    private fun saveToMovies(context: Context, file: File, title: String): Uri {
        val safeName = title.replace(Regex("[^A-Za-z0-9_-]+"), "_").trim('_').take(35).ifBlank { "VideoFactory" }
        val values = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, safeName + "_" + System.currentTimeMillis() + ".mp4")
            put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/VideoFactory")
                put(MediaStore.Video.Media.IS_PENDING, 1)
            }
        }
        val uri = context.contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values)
            ?: error("Hindi makagawa ng MP4 entry sa Movies/VideoFactory.")
        try {
            context.contentResolver.openOutputStream(uri, "w").use { stream ->
                checkNotNull(stream) { "Hindi mabuksan ang output file." }
                FileInputStream(file).use { input -> input.copyTo(stream) }
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val done = ContentValues().apply { put(MediaStore.Video.Media.IS_PENDING, 0) }
                context.contentResolver.update(uri, done, null, null)
            }
            return uri
        } catch (e: Exception) {
            context.contentResolver.delete(uri, null, null)
            throw e
        }
    }
}
