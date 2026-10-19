package com.paovideofactory.app

import android.os.Bundle
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
        setContent { VideoFactoryScreen(onSpeak = { text ->
            if (ttsReady) tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "vf-narration")
            else Toast.makeText(this, "Hindi pa handa ang Text-to-Speech sa device.", Toast.LENGTH_LONG).show()
        }) }
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
private fun VideoFactoryScreen(onSpeak: (String) -> Unit) {
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

            // Vertical preview mockup for the first milestone; MP4 export is a later milestone.
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
                "MVP 0.1 • Content generator + TTS preview. Actual MP4 rendering and export will be added next.",
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
