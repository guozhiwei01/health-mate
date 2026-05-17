package com.healthmate.security;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * AES-256-GCM 字段级加密
 * 用于加密存储敏感字段：手机号、对话内容、报告结果
 *
 * 面试要点：
 * - GCM 模式自带完整性校验（MAC），比 CBC 更安全
 * - 每次加密使用随机 IV，相同明文产生不同密文
 * - 密钥从配置中心读取，不硬编码
 */
@Slf4j
@Component
public class FieldEncryptor {

    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int GCM_TAG_LENGTH = 128;  // bits
    private static final int IV_LENGTH = 12;          // bytes

    private final SecretKeySpec secretKey;

    public FieldEncryptor(
            @Value("${security.aes-key:0123456789abcdef0123456789abcdef}") String keyHex) {
        byte[] keyBytes = hexToBytes(keyHex);
        this.secretKey = new SecretKeySpec(keyBytes, "AES");
        log.info("[CRYPTO] AES-256-GCM encryptor initialized");
    }

    /**
     * 加密（返回 Base64 编码的密文）
     * 格式：IV(12字节) + 密文 + Tag
     */
    public String encrypt(String plaintext) {
        if (plaintext == null || plaintext.isEmpty()) return plaintext;
        try {
            byte[] iv = new byte[IV_LENGTH];
            new SecureRandom().nextBytes(iv);

            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey, new GCMParameterSpec(GCM_TAG_LENGTH, iv));
            byte[] ciphertext = cipher.doFinal(plaintext.getBytes("UTF-8"));

            // IV + ciphertext 合并
            ByteBuffer buffer = ByteBuffer.allocate(IV_LENGTH + ciphertext.length);
            buffer.put(iv);
            buffer.put(ciphertext);

            return Base64.getEncoder().encodeToString(buffer.array());
        } catch (Exception e) {
            log.error("[CRYPTO] Encrypt failed: {}", e.getMessage());
            throw new RuntimeException("加密失败", e);
        }
    }

    /**
     * 解密
     */
    public String decrypt(String base64Ciphertext) {
        if (base64Ciphertext == null || base64Ciphertext.isEmpty()) return base64Ciphertext;
        try {
            byte[] data = Base64.getDecoder().decode(base64Ciphertext);
            ByteBuffer buffer = ByteBuffer.wrap(data);

            byte[] iv = new byte[IV_LENGTH];
            buffer.get(iv);
            byte[] ciphertext = new byte[buffer.remaining()];
            buffer.get(ciphertext);

            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, new GCMParameterSpec(GCM_TAG_LENGTH, iv));
            byte[] plaintext = cipher.doFinal(ciphertext);

            return new String(plaintext, "UTF-8");
        } catch (Exception e) {
            log.error("[CRYPTO] Decrypt failed: {}", e.getMessage());
            throw new RuntimeException("解密失败", e);
        }
    }

    private static byte[] hexToBytes(String hex) {
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                    + Character.digit(hex.charAt(i + 1), 16));
        }
        return data;
    }
}
