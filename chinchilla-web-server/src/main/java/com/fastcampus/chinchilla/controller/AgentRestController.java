package com.fastcampus.chinchilla.controller;

import com.fastcampus.chinchilla.dto.AgentRequest;
import com.fastcampus.chinchilla.dto.AgentResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api")
public class AgentRestController {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    @Value("${agent.api.url:http://localhost:8000}")
    private String agentApiUrl;

    @PostMapping("/chat")
    public ResponseEntity<AgentResponse> sendMessage(@RequestBody Map<String, Object> request) {
        try {
            // 카테고리 추출
            String category = (String) request.get("category");
            
            // 카테고리별 payload 구성
            Object payload = null;
            if ("jobs".equals(category)) {
                // 일자리 매칭의 경우
                Map<String, Object> payloadMap = new HashMap<>();
                payloadMap.put("query", request.get("query"));
                
                // 프로필 정보 구성
                Map<String, Object> profile = new HashMap<>();
                profile.put("age", request.get("age"));
                profile.put("gender", request.get("gender"));
                profile.put("location", request.get("location"));
                payloadMap.put("profile", profile);
                
                payload = payloadMap;
            } else {
                // 다른 카테고리의 경우 (추후 구현)
                Map<String, Object> payloadMap = new HashMap<>();
                payloadMap.put("query", request.get("query"));
                payload = payloadMap;
            }
            
            // Agent API 요청 생성
            AgentRequest agentRequest = new AgentRequest(category, payload);
            
            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            // HTTP 요청 생성
            HttpEntity<AgentRequest> entity = new HttpEntity<>(agentRequest, headers);
            
            // API 호출
            ResponseEntity<AgentResponse> response = restTemplate.exchange(
                agentApiUrl + "/agent/query",
                HttpMethod.POST,
                entity,
                AgentResponse.class
            );
            
            return response;
            
        } catch (Exception e) {
            log.info("AgentRestController : error => {}", e.getMessage());
            // 에러 발생 시 기본 응답 반환
            AgentResponse errorResponse = new AgentResponse();
            errorResponse.setAnswer("죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }
}
