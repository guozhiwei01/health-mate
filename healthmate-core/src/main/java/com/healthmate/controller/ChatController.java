package com.healthmate.controller;

import com.healthmate.client.AiEngineClient;
import com.healthmate.entity.Conversation;
import com.healthmate.entity.Message;
import com.healthmate.service.ChatService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import reactor.core.publisher.Flux;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * 对话接口
 * POST /api/chat           同步对话
 * POST /api/chat/stream    SSE 流式对话
 * GET  /api/conversations   会话列表
 * GET  /api/conversations/{id}/messages  消息历史
 */
@Slf4j
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;
    private final AiEngineClient aiEngineClient;

    /**
     * 同步对话
     */
    @PostMapping("/chat")
    public ResponseEntity<Map<String, Object>> chat(@RequestBody ChatRequest request) {
        long startTime = System.currentTimeMillis();

        // Ensure conversation exists
        String convId = request.getConversationId();
        if (convId == null || convId.isEmpty()) {
            Conversation conv = chatService.createConversation(request.getUserId());
            convId = conv.getId();
        }

        // Call AI Engine
        int turnCount = chatService.getMessages(convId).size() / 2;
        AiEngineClient.ChatResponse aiResp = aiEngineClient.chat(
                request.getUserInput(), convId, turnCount
        );

        int latencyMs = (int) (System.currentTimeMillis() - startTime);

        // Save messages
        chatService.saveMessagePair(
                convId, request.getUserInput(),
                aiResp.getResponse(), aiResp.getIntent(),
                aiResp.getModel(), latencyMs
        );

        return ResponseEntity.ok(Map.of(
                "conversationId", convId,
                "response", aiResp.getResponse(),
                "intent", aiResp.getIntent(),
                "model", aiResp.getModel(),
                "latencyMs", latencyMs
        ));
    }

    /**
     * SSE 流式对话 — 透传 Python AI Engine 的 SSE 流
     */
    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chatStream(@RequestBody ChatRequest request) {
        SseEmitter emitter = new SseEmitter(60_000L);

        String convId = request.getConversationId();
        if (convId == null || convId.isEmpty()) {
            Conversation conv = chatService.createConversation(request.getUserId());
            convId = conv.getId();
        }

        int turnCount = chatService.getMessages(convId).size() / 2;
        final String finalConvId = convId;
        final long startTime = System.currentTimeMillis();
        final StringBuilder fullResponse = new StringBuilder();

        Flux<String> stream = aiEngineClient.chatStream(
                request.getUserInput(), convId, turnCount
        );

        stream.subscribe(
                data -> {
                    try {
                        emitter.send(SseEmitter.event().data(data));
                        // Collect full response for persistence
                        if (data.contains("\"type\":\"token\"")) {
                            // Extract content from JSON
                            int idx = data.indexOf("\"content\":\"");
                            if (idx >= 0) {
                                int start = idx + 11;
                                int end = data.lastIndexOf("\"");
                                if (end > start) {
                                    fullResponse.append(data, start, end);
                                }
                            }
                        }
                    } catch (IOException e) {
                        emitter.completeWithError(e);
                    }
                },
                error -> {
                    log.error("[CHAT-STREAM] Error: {}", error.getMessage());
                    emitter.completeWithError(error);
                },
                () -> {
                    // Save after stream completes
                    int latencyMs = (int) (System.currentTimeMillis() - startTime);
                    chatService.saveMessagePair(
                            finalConvId, request.getUserInput(),
                            fullResponse.toString(), "", "", latencyMs
                    );
                    emitter.complete();
                }
        );

        return emitter;
    }

    /**
     * 会话列表
     */
    @GetMapping("/conversations")
    public ResponseEntity<List<Conversation>> listConversations(
            @RequestParam Long userId) {
        return ResponseEntity.ok(chatService.listConversations(userId));
    }

    /**
     * 消息历史
     */
    @GetMapping("/conversations/{id}/messages")
    public ResponseEntity<List<Message>> getMessages(@PathVariable String id) {
        return ResponseEntity.ok(chatService.getMessages(id));
    }

    @Data
    public static class ChatRequest {
        private Long userId;
        private String conversationId;
        private String userInput;
    }
}
