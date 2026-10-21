package com.paovideofactory.app

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Locally encrypted owner-issued Worker token. Never put server secrets in the APK. */
class ConnectionSettings(context: Context) {
    private val prefs = context.getSharedPreferences("vf_connection", Context.MODE_PRIVATE)
    private val alias = "vf_content_kit_token"

    fun url(): String = prefs.getString("worker_url", "").orEmpty()

    fun token(): String = runCatching {
        val payload = prefs.getString("access_token", null) ?: return ""
        val bytes = Base64.decode(payload, Base64.NO_WRAP)
        if (bytes.size < 13) return ""
        val iv = bytes.copyOfRange(0, 12)
        val data = bytes.copyOfRange(12, bytes.size)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), GCMParameterSpec(128, iv))
        String(cipher.doFinal(data), Charsets.UTF_8)
    }.getOrDefault("")

    fun save(endpoint: String, accessToken: String) {
        require(endpoint.startsWith("https://")) { "HTTPS URL is required" }
        require(accessToken.length >= 12) { "Token must be at least 12 characters" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val content = cipher.iv + cipher.doFinal(accessToken.toByteArray(Charsets.UTF_8))
        prefs.edit()
            .putString("worker_url", endpoint.trim().trimEnd('/'))
            .putString("access_token", Base64.encodeToString(content, Base64.NO_WRAP))
            .apply()
    }

    private fun getOrCreateKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey(alias, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                alias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
    }
}
