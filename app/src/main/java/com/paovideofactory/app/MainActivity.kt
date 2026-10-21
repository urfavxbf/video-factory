package com.paovideofactory.app

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private val Navy = Color(0xFF0D1525)
private val Surface = Color(0xFF17233A)
private val Mint = Color(0xFF7BEBC8)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val settings = ConnectionSettings(this)
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Mint, background = Navy, surface = Surface,
                    secondary = Color(0xFF8EBCFF)
                )
            ) {
                ContentStudio(settings)
            }
        }
    }
}

@Composable
private fun ContentStudio(settings: ConnectionSettings) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val scope = rememberCoroutineScope()
    val history = remember { VideoHistory(context) }
    var endpoint by remember { mutableStateOf(settings.url()) }
    var token by remember { mutableStateOf(settings.token()) }
    var showSetup by remember { mutableStateOf(endpoint.isBlank() || token.isBlank()) }
    var topic by rememberSaveable { mutableStateOf("") }
    var angle by rememberSaveable { mutableStateOf("") }
    var kit by remember { mutableStateOf<ContentKit?>(null) }
    var isGenerating by remember { mutableStateOf(false) }
    var isLoadingAssets by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("Ilagay ang paksa para gumawa ng original content kit.") }
    var mediaKind by remember { mutableStateOf("videos") }
    var selectedQuery by remember { mutableStateOf("") }
    var media by remember { mutableStateOf<List<MediaAsset>>(emptyList()) }
    var selectedAsset by remember { mutableStateOf<MediaAsset?>(null) }

    fun loadAssets(query: String, kind: String) {
        selectedQuery = query
        mediaKind = kind
        media = emptyList()
        isLoadingAssets = true
        scope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    ContentKitApi(endpoint, token).searchMedia(query, kind)
                }
            }.onSuccess {
                media = it
                message = if (it.isEmpty()) "Walang media. Pumili ng ibang scene search." else "Tap Save para makuha ang file."
            }.onFailure {
                message = "Media search: " + (it.message ?: "Hindi makakonekta.")
            }
            isLoadingAssets = false
        }
    }

    fun onDocumentChosen(uri: Uri?) {
        val asset = selectedAsset ?: return
        if (uri == null) return
        message = "Sina-save ang " + asset.type + " sa pinili mong folder..."
        scope.launch {
            runCatching { withContext(Dispatchers.IO) { saveAsset(context, uri, asset) } }
                .onSuccess { message = "File saved. Buksan ang CapCut at i-import ito." }
                .onFailure { message = "Hindi na-save: " + (it.message ?: "Download failed.") }
        }
    }

    val saveVideo = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("video/mp4")
    ) { uri -> onDocumentChosen(uri) }
    val saveImage = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("image/jpeg")
    ) { uri -> onDocumentChosen(uri) }
    val saveKit = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("text/plain")
    ) { uri ->
        val current = kit
        if (uri != null && current != null) {
            scope.launch {
                runCatching {
                    withContext(Dispatchers.IO) {
                        context.contentResolver.openOutputStream(uri)?.bufferedWriter()?.use {
                            it.write(current.textExport())
                        } ?: error("Cannot write content kit")
                    }
                }.onSuccess { message = "Content kit saved as text file." }
                    .onFailure { message = "Export error: " + (it.message ?: "Unknown") }
            }
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().background(Navy)
            .verticalScroll(rememberScrollState()).padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("VIDEO FACTORY", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
        Text("Filipino Creator Kit  •  ElevenLabs + CapCut", color = Mint)

        ElevatedCard(colors = CardDefaults.elevatedCardColors(containerColor = Surface)) {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("PRIVATE AI CONNECTION", modifier = Modifier.weight(1f), fontWeight = FontWeight.Bold)
                    TextButton(onClick = { showSetup = !showSetup }) {
                        Text(if (showSetup) "Hide" else "Edit")
                    }
                }
                if (showSetup) {
                    OutlinedTextField(
                        value = endpoint, onValueChange = { endpoint = it },
                        label = { Text("Cloudflare Worker HTTPS URL") },
                        modifier = Modifier.fillMaxWidth(), singleLine = true
                    )
                    OutlinedTextField(
                        value = token, onValueChange = { token = it },
                        label = { Text("App access token") },
                        visualTransformation = PasswordVisualTransformation(),
                        modifier = Modifier.fillMaxWidth(), singleLine = true
                    )
                    Text(
                        "Server credentials para sa AI at Pixabay ay nasa Worker. " +
                            "Owner-issued access token lang ang ilalagay rito.",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Button(onClick = {
                        runCatching {
                            ContentKitApi(endpoint, token)
                            settings.save(endpoint.trim(), token)
                        }.onSuccess {
                            showSetup = false
                            message = "Private connection saved."
                        }.onFailure {
                            message = "Connection settings: " + (it.message ?: "Invalid input.")
                        }
                    }) { Text("Save private connection") }
                }
            }
        }

        ElevatedCard(colors = CardDefaults.elevatedCardColors(containerColor = Surface)) {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("01  /  CREATE EPISODE", color = Mint, fontWeight = FontWeight.Bold)
                OutlinedTextField(
                    value = topic, onValueChange = { topic = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Video topic") },
                    placeholder = { Text("Hal. bakit umiinit ang phone habang nagcha-charge?") },
                    minLines = 2, maxLines = 4
                )
                OutlinedTextField(
                    value = angle, onValueChange = { angle = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Optional angle / audience") },
                    placeholder = { Text("Hal. pang beginners, practical at madaling intindihin") },
                    minLines = 1, maxLines = 3
                )
                Button(
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !isGenerating && topic.trim().length >= 5 && !showSetup,
                    onClick = {
                        isGenerating = true
                        message = "Gumagawa ng original Filipino content kit..."
                        scope.launch {
                            runCatching {
                                withContext(Dispatchers.IO) {
                                    ContentKitApi(endpoint, token).generate(topic, angle, history.recentTitles())
                                }
                            }.onSuccess { created ->
                                kit = created
                                history.addTitle(created.title)
                                message = "AI draft created. Review facts bago i-publish."
                                loadAssets(created.visualQueries.first(), "videos")
                            }.onFailure {
                                message = "Hindi nagawa ang content kit: " + (it.message ?: "Try again.")
                            }
                            isGenerating = false
                        }
                    }
                ) {
                    if (isGenerating) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    else Text("Generate original content kit")
                }
            }
        }

        Text(message, style = MaterialTheme.typography.bodySmall, color = Mint)

        kit?.let { current ->
            Section("02  /  WRITING KIT") {
                Text("AI-written draft • fact-check before publishing", style = MaterialTheme.typography.bodySmall)
                CopyText("VIDEO TITLE", current.title, context)
                CopyText("VIDEO HOOK", current.hook, context)
                CopyText("ELEVENLABS VOICE-OVER SCRIPT", current.script, context)
                OutlinedButton(onClick = { openExternal(context, "https://elevenlabs.io/") }) {
                    Text("Open ElevenLabs")
                }
                CopyText("YOUTUBE CAPTION / DESCRIPTION", current.caption, context)
                CopyText("HASHTAGS", current.hashtags.joinToString(" "), context)
                if (current.sourceNote.isNotBlank()) {
                    Text("Review these claims: " + current.sourceNote,
                        style = MaterialTheme.typography.bodySmall, color = Color(0xFFFFD399))
                }
                OutlinedButton(onClick = { saveKit.launch("VideoFactory_Content_Kit.txt") }) {
                    Text("Save complete kit (.txt)")
                }
            }

            Section("03  /  PICTURES AND VIDEOS FOR CAPCUT") {
                Text("Choose the scene to find matching stock assets. Pixabay creators are credited on each result.",
                    style = MaterialTheme.typography.bodySmall)
                current.visualQueries.forEachIndexed { index, query ->
                    OutlinedButton(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = { loadAssets(query, mediaKind) },
                        enabled = !isLoadingAssets
                    ) {
                        Text("Scene " + (index + 1) + "  •  " + query)
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    FilterChip(
                        selected = mediaKind == "videos",
                        onClick = { if (!isLoadingAssets) loadAssets(selectedQuery.ifBlank {
                            current.visualQueries.first()
                        }, "videos") },
                        label = { Text("Videos") }
                    )
                    FilterChip(
                        selected = mediaKind == "images",
                        onClick = { if (!isLoadingAssets) loadAssets(selectedQuery.ifBlank {
                            current.visualQueries.first()
                        }, "images") },
                        label = { Text("Pictures") }
                    )
                }
                if (isLoadingAssets) {
                    CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
                } else if (media.isEmpty()) {
                    Text("No media loaded. Choose a scene or try Pictures.")
                } else {
                    media.forEach { asset ->
                        MediaCard(asset, onSave = {
                            selectedAsset = asset
                            if (asset.type == "video") saveVideo.launch("VF_" + asset.id + ".mp4")
                            else saveImage.launch("VF_" + asset.id + ".jpg")
                        }, onSource = { openExternal(context, asset.pageUrl) })
                    }
                }
                OutlinedButton(onClick = { openExternal(context, "https://www.capcut.com/") }) {
                    Text("Open CapCut website")
                }
                Text(
                    "Import downloaded files into CapCut. Confirm media rights, " +
                        "relevance and whether altered/synthetic disclosure is required before publishing.",
                    style = MaterialTheme.typography.bodySmall, color = Color.LightGray
                )
            }

            Section("04  /  BACKGROUND MUSIC FOR CAPCUT") {
                Text(
                    "Pumili ng music mood na bagay sa episode. Browse at i-download ang MP3 " +
                        "sa official Mixkit page, saka i-import sa CapCut.",
                    style = MaterialTheme.typography.bodySmall
                )
                val musicChoices = remember(current) { MusicResources.suggestions(current) }
                musicChoices.forEachIndexed { index, mood ->
                    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                        Text(
                            (if (index == 0) "RECOMMENDED  •  " else "ALTERNATIVE  •  ") + mood.name,
                            color = if (index == 0) Mint else Color.White,
                            fontWeight = FontWeight.Bold
                        )
                        Text(mood.description, style = MaterialTheme.typography.bodySmall)
                        Text("Editing tip: " + mood.editingTip,
                            style = MaterialTheme.typography.bodySmall, color = Color.LightGray)
                        OutlinedButton(
                            modifier = Modifier.fillMaxWidth(),
                            onClick = { openExternal(context, mood.mixkitUrl) }
                        ) { Text("Browse / download music on Mixkit") }
                        HorizontalDivider(color = Color(0xFF36485F))
                    }
                }
                OutlinedButton(
                    modifier = Modifier.fillMaxWidth(),
                    onClick = { openExternal(context, MusicResources.youtubeAudioLibraryUrl) }
                ) { Text("Open YouTube Audio Library") }
                Text(
                    "Sa YouTube Studio Audio Library, puwedeng pumili ng mood at mag-download ng MP3. " +
                        "Kung Attribution required ang track, kopyahin ang credit para sa description.",
                    style = MaterialTheme.typography.bodySmall
                )
                TextButton(onClick = { openExternal(context, MusicResources.mixkitLicenseUrl) }) {
                    Text("Read Mixkit music license")
                }
                Text(
                    "Hindi pa direct in-app audio download ito. Bawat track ay may sariling license; " +
                        "i-check bago gamitin, at huwag i-register sa Content ID. " +
                        "Hinaan ang background music para malinaw ang ElevenLabs narration.",
                    style = MaterialTheme.typography.bodySmall, color = Color.LightGray
                )
            }
        }

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun Section(title: String, content: @Composable ColumnScope.() -> Unit) {
    ElevatedCard(colors = CardDefaults.elevatedCardColors(containerColor = Surface)) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            content = {
                Text(title, color = Mint, fontWeight = FontWeight.Bold)
                content()
            }
        )
    }
}

@Composable
private fun CopyText(label: String, value: String, context: Context) {
    Text(label, style = MaterialTheme.typography.labelMedium, color = Mint)
    Text(value, style = MaterialTheme.typography.bodyMedium)
    OutlinedButton(onClick = {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText(label, value))
        Toast.makeText(context, label + " copied", Toast.LENGTH_SHORT).show()
    }) { Text("Copy") }
    HorizontalDivider(color = Color(0xFF36485F))
}

@Composable
private fun MediaCard(asset: MediaAsset, onSave: () -> Unit, onSource: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF202F49)),
        shape = RoundedCornerShape(14.dp)
    ) {
        Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            AsyncImage(
                model = asset.previewUrl,
                contentDescription = "Pixabay " + asset.type + " by " + asset.creator,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxWidth().height(160.dp)
            )
            Text("Pixabay  •  " + asset.creator, style = MaterialTheme.typography.labelSmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onSave) { Text("Save " + asset.type) }
                OutlinedButton(onClick = onSource) { Text("Source / license") }
            }
        }
    }
}

private fun openExternal(context: Context, url: String) {
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
    runCatching { context.startActivity(intent) }
        .onFailure { Toast.makeText(context, "Cannot open link.", Toast.LENGTH_SHORT).show() }
}
