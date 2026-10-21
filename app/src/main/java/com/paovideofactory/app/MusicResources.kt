package com.paovideofactory.app

import java.util.Locale

/**
 * Hand-curated official music-library categories, not fabricated tracks or direct download URLs.
 * Each link opens the provider's own download and license flow in the browser.
 */
data class MusicMood(
    val name: String,
    val description: String,
    val editingTip: String,
    val mixkitUrl: String
)

object MusicResources {
    const val youtubeAudioLibraryUrl = "https://www.youtube.com/audiolibrary"
    const val mixkitLicenseUrl = "https://mixkit.co/license/modal/musicFree/"

    private val mysterious = MusicMood(
        "Curious / Mysterious",
        "Subtle tension, curious discoveries, human behavior and psychology.",
        "Use a soft instrumental bed; raise it slightly after the hook.",
        "https://mixkit.co/free-stock-music/mood/mysterious/"
    )
    private val calm = MusicMood(
        "Calm / Thoughtful",
        "Reflective explanations, personal stories and quiet realizations.",
        "Keep the music below the ElevenLabs voice; avoid busy melodies.",
        "https://mixkit.co/free-stock-music/mood/calm/"
    )
    private val atmospheric = MusicMood(
        "Ambient / Documentary",
        "Science, facts, explanatory shorts and neutral narration.",
        "Choose minimal background music without distracting vocals.",
        "https://mixkit.co/free-stock-music/mood/atmospheric/"
    )
    private val dramatic = MusicMood(
        "Dramatic / Tension",
        "Suspense, cautionary stories or a serious reveal.",
        "Use tension sparingly; lower the volume for the explanation.",
        "https://mixkit.co/free-stock-music/mood/dramatic/"
    )
    private val uplifting = MusicMood(
        "Uplifting / Motivating",
        "Growth, confidence, achievements and practical advice.",
        "Build energy toward the takeaway without masking narration.",
        "https://mixkit.co/free-stock-music/mood/uplifting/"
    )
    private val playful = MusicMood(
        "Playful / Light",
        "Everyday humor, relatable mistakes and a lighter vibe.",
        "Let comedic beats breathe and keep voice-over intelligible.",
        "https://mixkit.co/free-stock-music/mood/playful/"
    )

    fun suggestions(kit: ContentKit): List<MusicMood> {
        val text = (kit.title + " " + kit.hook).lowercase(Locale.ROOT)
        val picks = when {
            listOf("psycholog", "spotlight", "mind", "isip", "utak", "behavior",
                "mental", "bias", "tao", "pagkakamali").any { text.contains(it) } ->
                listOf(mysterious, calm, atmospheric)
            listOf("takot", "kaba", "danger", "panganib", "scary", "horror",
                "kaso", "crime", "misteryo", "mystery").any { text.contains(it) } ->
                listOf(dramatic, mysterious, atmospheric)
            listOf("motiv", "succeed", "success", "pagsisikap", "pangarap",
                "tiwala", "confidence", "inspir", "pag-asa").any { text.contains(it) } ->
                listOf(uplifting, calm, atmospheric)
            listOf("nakakatawa", "tawa", "funny", "joke", "kulit",
                "kalokohan", "patawa").any { text.contains(it) } ->
                listOf(playful, uplifting, calm)
            listOf("heart", "puso", "breakup", "sad", "lungkot", "love",
                "relasyon", "pag-ibig").any { text.contains(it) } ->
                listOf(calm, mysterious, atmospheric)
            else -> listOf(atmospheric, mysterious, calm)
        }
        return picks.distinctBy { it.name }
    }
}
