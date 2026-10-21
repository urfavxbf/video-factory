package com.paovideofactory.app

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class ContentKit(
    val title: String,
    val script: String,
    val caption: String,
    val hook: String,
    val hashtags: List<String>,
    val visualQueries: List<String>,
    val sourceNote: String
) {
    fun textExport(): String = buildString {
        appendLine("VIDEO FACTORY — FILIPINO CONTENT KIT")
        appendLine("EDITORIAL DRAFT — verify facts and media rights before publishing")
        appendLine()
        appendLine("TITLE: " + title)
        appendLine("HOOK: " + hook)
        appendLine()
        appendLine("VOICE OVER — copy into ElevenLabs")
        appendLine(script)
        appendLine()
        appendLine("CAPTION: " + caption)
        appendLine("HASHTAGS: " + hashtags.joinToString(" "))
        appendLine()
        appendLine("CAPCUT SHOT SEARCHES")
        visualQueries.forEachIndexed { index, query -> appendLine((index + 1).toString() + ". " + query) }
        appendLine()
        appendLine("FACT REVIEW: " + sourceNote)
        appendLine("Media source: Pixabay — check each contributor page and Content License.")
    }
}

data class MediaAsset(
    val id: String,
    val type: String,
    val previewUrl: String,
    val downloadUrl: String,
    val pageUrl: String,
    val creator: String
)

class ContentKitApi(endpoint: String, private val accessToken: String) {
    private val baseUrl: String = endpoint.trim().trimEnd('/').also {
        require(it.startsWith("https://") && URL(it).host.isNotBlank()) {
            "HTTPS Worker URL ang kailangan."
        }
        require(accessToken.isNotBlank()) { "Kailangan ang private access token." }
    }

    fun generate(topic: String, angle: String, previousTitles: List<String>): ContentKit {
        val request = JSONObject().apply {
            put("topic", topic.trim())
            put("angle", angle.trim())
            put("previousTitles", JSONArray(previousTitles.takeLast(15)))
        }
        val json = httpJson("$baseUrl/v1/generate", "POST", request.toString())
        val queryArray = json.getJSONArray("visualQueries")
        val tagsArray = json.getJSONArray("hashtags")
        return ContentKit(
            title = json.getString("title"),
            script = json.getString("script"),
            caption = json.getString("caption"),
            hook = json.getString("hook"),
            hashtags = (0 until tagsArray.length()).map { tagsArray.getString(it) },
            visualQueries = (0 until queryArray.length()).map { queryArray.getString(it) },
            sourceNote = json.optString("sourceNote")
        )
    }

    fun searchMedia(query: String, kind: String): List<MediaAsset> {
        require(kind == "videos" || kind == "images")
        val encoded = URLEncoder.encode(query, "UTF-8")
        val json = httpJson("$baseUrl/v1/assets?kind=$kind&query=$encoded", "GET", null)
        val rows = json.getJSONArray("results")
        return (0 until rows.length()).map { index ->
            val row = rows.getJSONObject(index)
            MediaAsset(
                id = row.getString("id"),
                type = row.getString("type"),
                previewUrl = row.getString("previewUrl"),
                downloadUrl = row.getString("downloadUrl"),
                pageUrl = row.getString("pageUrl"),
                creator = row.optString("creator", "Pixabay contributor")
            )
        }
    }

    private fun httpJson(url: String, method: String, body: String?): JSONObject {
        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 15_000
            readTimeout = 90_000
            setRequestProperty("Authorization", "Bearer $accessToken")
            setRequestProperty("Accept", "application/json")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }
        return try {
            if (body != null) conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val message = stream?.bufferedReader()?.use { it.readText().take(1_000_000) }.orEmpty()
            val result = runCatching { JSONObject(message) }.getOrNull()
            if (code !in 200..299) {
                val serverMessage = result?.optString("error").orEmpty()
                throw IOException(
                    if (code == 401) "Mali ang app access token."
                    else serverMessage.ifBlank { "Server error ($code)." }
                )
            }
            result ?: throw IOException("Invalid server response.")
        } finally {
            conn.disconnect()
        }
    }
}

class VideoHistory(private val context: Context) {
    private val prefs = context.getSharedPreferences("video_factory_history", Context.MODE_PRIVATE)
    fun recentTitles(): List<String> {
        val content = prefs.getString("recent_titles", "[]").orEmpty()
        return runCatching {
            val array = JSONArray(content)
            (0 until array.length()).map { array.getString(it) }
        }.getOrDefault(emptyList())
    }

    fun addTitle(title: String) {
        val current = recentTitles().filterNot { it.equals(title, ignoreCase = true) }
        prefs.edit().putString(
            "recent_titles",
            JSONArray((current + title).takeLast(15)).toString()
        ).apply()
    }
}

fun saveAsset(context: Context, destination: Uri, asset: MediaAsset) {
    val parsed = URL(asset.downloadUrl)
    require(parsed.protocol == "https" && (
        parsed.host.equals("pixabay.com", true) ||
            parsed.host.endsWith(".pixabay.com", true)
        )) { "Only official Pixabay media URLs can be saved." }

    val connection = (parsed.openConnection() as HttpURLConnection).apply {
        connectTimeout = 15_000
        readTimeout = 60_000
        instanceFollowRedirects = true
    }
    try {
        if (connection.responseCode !in 200..299) {
            throw IOException("Media download unavailable (" + connection.responseCode + ").")
        }
        val maxBytes = 120L * 1024L * 1024L
        val expected = connection.contentLengthLong
        if (expected > maxBytes) throw IOException("Media file exceeds 120 MB.")
        context.contentResolver.openOutputStream(destination)?.use { out ->
            connection.inputStream.use { input ->
                val buffer = ByteArray(64 * 1024)
                var downloaded = 0L
                while (true) {
                    val length = input.read(buffer)
                    if (length < 0) break
                    downloaded += length
                    if (downloaded > maxBytes) throw IOException("Media file exceeds 120 MB.")
                    out.write(buffer, 0, length)
                }
                if (downloaded == 0L) throw IOException("Empty media download.")
            }
        } ?: throw IOException("Cannot open save location.")
    } finally {
        connection.disconnect()
    }
}
