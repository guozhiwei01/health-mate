package com.healthmate.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.healthmate.entity.Conversation;
import com.healthmate.entity.Message;
import com.healthmate.mapper.ConversationMapper;
import com.healthmate.mapper.MessageMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/**
 * 会话管理 Service
 * - 创建/查询会话
 * - 保存对话消息
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ChatService {

    private final ConversationMapper conversationMapper;
    private final MessageMapper messageMapper;

    /**
     * 创建新会话
     */
    public Conversation createConversation(Long userId) {
        Conversation conv = new Conversation();
        conv.setId(UUID.randomUUID().toString().replace("-", ""));
        conv.setUserId(userId);
        conv.setTitle("新对话");
        conv.setMessageCount(0);
        conversationMapper.insert(conv);
        log.info("[CHAT] Created conversation: {} for user: {}", conv.getId(), userId);
        return conv;
    }

    /**
     * 获取用户的会话列表
     */
    public List<Conversation> listConversations(Long userId) {
        return conversationMapper.selectList(
                new LambdaQueryWrapper<Conversation>()
                        .eq(Conversation::getUserId, userId)
                        .orderByDesc(Conversation::getUpdatedAt)
        );
    }

    /**
     * 保存用户消息 + AI 回复
     */
    @Transactional
    public void saveMessagePair(String conversationId, String userInput,
                                 String aiResponse, String intent, String model,
                                 int latencyMs) {
        // User message
        Message userMsg = new Message();
        userMsg.setConversationId(conversationId);
        userMsg.setRole("user");
        userMsg.setContent(userInput);
        messageMapper.insert(userMsg);

        // AI message
        Message aiMsg = new Message();
        aiMsg.setConversationId(conversationId);
        aiMsg.setRole("assistant");
        aiMsg.setContent(aiResponse);
        aiMsg.setModel(model);
        aiMsg.setLatencyMs(latencyMs);
        messageMapper.insert(aiMsg);

        // Update conversation
        Conversation conv = conversationMapper.selectById(conversationId);
        if (conv != null) {
            conv.setMessageCount(conv.getMessageCount() + 2);
            conv.setLastIntent(intent);
            // Auto-generate title from first user message
            if ("新对话".equals(conv.getTitle())) {
                conv.setTitle(userInput.length() > 20
                        ? userInput.substring(0, 20) + "..."
                        : userInput);
            }
            conversationMapper.updateById(conv);
        }
    }

    /**
     * 获取会话的消息历史
     */
    public List<Message> getMessages(String conversationId) {
        return messageMapper.selectList(
                new LambdaQueryWrapper<Message>()
                        .eq(Message::getConversationId, conversationId)
                        .orderByAsc(Message::getCreatedAt)
        );
    }
}
