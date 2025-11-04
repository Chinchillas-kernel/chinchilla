package com.fastcampus.chinchilla.controller;

import com.fastcampus.chinchilla.config.CommonUtil;
import com.fastcampus.chinchilla.dto.AgentRequest;
import com.fastcampus.chinchilla.dto.AgentResponse;
import com.fastcampus.chinchilla.dto.JobsPayload;
import com.fastcampus.chinchilla.dto.JobsProfile;
import com.fastcampus.chinchilla.dto.LegalPayload;
import com.fastcampus.chinchilla.dto.LegalProfile;
import com.fastcampus.chinchilla.dto.NewsPayload;
import com.fastcampus.chinchilla.dto.ScamDefensePayload;
import com.fastcampus.chinchilla.dto.WelfarePayload;
import com.fasterxml.jackson.core.JsonProcessingException;
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
    private final CommonUtil commonUtil;

    @Value("${agent.api.url:http://localhost:8000}")
    private String agentApiUrl;

    @PostMapping("/chat")
    public ResponseEntity<AgentResponse> sendMessage(@RequestBody Map<String, Object> request) {
        try {
            // 카테고리 추출
            String category = (String) request.get("category");
            
            // 카테고리별 payload 구성
            Object payload = buildPayload(category, request);
            
            // Agent API 요청 생성
            AgentRequest agentRequest = new AgentRequest(category, payload);
            
            // HTTP 헤더 설정
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            // HTTP 요청 생성
            HttpEntity<AgentRequest> entity = new HttpEntity<>(agentRequest, headers);
            
            // API 호출 (raw JSON 확보)
            ResponseEntity<String> response = restTemplate.exchange(
                agentApiUrl + "/agent/query",
                HttpMethod.POST,
                entity,
                String.class
            );

            String responseBody = response.getBody();
            log.info("AgentRestController : raw agent response => {}", responseBody);

            if (responseBody == null || responseBody.isBlank()) {
                log.warn("AgentRestController : empty response body from agent API");
                AgentResponse errorResponse = new AgentResponse();
                errorResponse.setAnswer("죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
            }

            try {
                AgentResponse agentResponse = objectMapper.readValue(responseBody, AgentResponse.class);
                String md = agentResponse.getAnswer();
                String html = (md == null || md.isBlank()) ? "" : commonUtil.markdown(md);
                agentResponse.setAnswerHtml(html);
                return ResponseEntity.status(response.getStatusCode()).body(agentResponse);
            } catch (JsonProcessingException e) {
                log.info(
                    "AgentRestController : failed to parse agent response. raw => {}",
                    responseBody,
                    e
                );
                AgentResponse errorResponse = new AgentResponse();
                errorResponse.setAnswer("죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
            }
            
        } catch (Exception e) {
            log.info("AgentRestController : error => {}", e.getMessage(), e);
            // 에러 발생 시 기본 응답 반환
            AgentResponse errorResponse = new AgentResponse();
            errorResponse.setAnswer("죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    private Object buildPayload(String category, Map<String, Object> request) {
        if (category == null) {
            throw new IllegalArgumentException("category is required");
        }

        Object rawPayload = request.get("payload");
        if (rawPayload instanceof Map<?, ?> payloadMap) {
            @SuppressWarnings("unchecked")
            Map<String, Object> typedPayload = new HashMap<>((Map<String, Object>) payloadMap);
            typedPayload.putIfAbsent("query", request.get("query"));
            return convertPayload(category, typedPayload);
        }

        return convertPayload(category, request);
    }

    private Object convertPayload(String category, Map<String, Object> source) {
        String query = asString(source.get("query"));
        if (query == null || query.isBlank()) {
            throw new IllegalArgumentException("query is required for category " + category);
        }

        switch (category) {
            case "jobs":
                Map<String, Object> profileSource = extractNestedMap(source.get("profile"));
                if (profileSource == null) {
                    profileSource = source;
                }

                Integer age = asInteger(firstNonNull(profileSource.get("age"), profileSource.get("userAge")));
                if (age == null) {
                    throw new IllegalArgumentException("jobs payload requires age");
                }

                JobsProfile jobsProfile = new JobsProfile(
                    age,
                    defaultString(asString(firstNonNull(profileSource.get("gender"), profileSource.get("userGender"))), "other"),
                    asString(firstNonNull(profileSource.get("location"), profileSource.get("userLocation")))
                );
                return new JobsPayload(query, jobsProfile);

            case "welfare":
                return new WelfarePayload(
                    query,
                    asString(firstNonNull(source.get("location"), source.get("region"))),
                    asString(firstNonNull(source.get("audience"), source.get("target")))
                );

            case "news":
                return new NewsPayload(
                    query,
                    asString(firstNonNull(source.get("category"), source.get("newsCategory"))),
                    asString(firstNonNull(source.get("date_from"), source.get("dateFrom"))),
                    asString(firstNonNull(source.get("date_to"), source.get("dateTo")))
                );

            case "legal":
                Map<String, Object> legalProfileSource = extractNestedMap(source.get("profile"));
                LegalProfile legalProfile = null;
                if (legalProfileSource != null || hasAnyLegalProfileFields(source)) {
                    Map<String, Object> profileMap = legalProfileSource != null ? legalProfileSource : source;
                    legalProfile = new LegalProfile(
                        asInteger(firstNonNull(profileMap.get("age"), profileMap.get("userAge"))),
                        asString(firstNonNull(profileMap.get("region"), profileMap.get("location"))),
                        asString(firstNonNull(profileMap.get("interest"), profileMap.get("topic"))),
                        asInteger(firstNonNull(profileMap.get("income"), profileMap.get("monthlyIncome")))
                    );
                }
                return new LegalPayload(query, legalProfile);

            case "scam_defense":
                return new ScamDefensePayload(
                    query,
                    asString(firstNonNull(source.get("sender"), source.get("phone"), source.get("contact")))
                );

            default:
                throw new IllegalArgumentException("Unsupported category: " + category);
        }
    }

    private Map<String, Object> extractNestedMap(Object value) {
        if (value instanceof Map<?, ?> mapValue) {
            @SuppressWarnings("unchecked")
            Map<String, Object> typedMap = new HashMap<>((Map<String, Object>) mapValue);
            return typedMap;
        }
        return null;
    }

    private boolean hasAnyLegalProfileFields(Map<String, Object> source) {
        return source.containsKey("age") ||
            source.containsKey("region") ||
            source.containsKey("interest") ||
            source.containsKey("income") ||
            source.containsKey("userAge") ||
            source.containsKey("monthlyIncome");
    }

    private Integer asInteger(Object value) {
        if (value == null) {
            return null;
        }
        if (value instanceof Integer integer) {
            return integer;
        }
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value instanceof String stringValue) {
            String trimmed = stringValue.trim();
            if (trimmed.isEmpty()) {
                return null;
            }
            try {
                return Integer.parseInt(trimmed);
            } catch (NumberFormatException e) {
                log.warn("AgentRestController : unable to parse integer from value '{}'", stringValue);
            }
        }
        return null;
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }

    private String defaultString(String value, String defaultValue) {
        return (value == null || value.isBlank()) ? defaultValue : value;
    }

    private Object firstNonNull(Object... values) {
        for (Object value : values) {
            if (value != null) {
                return value;
            }
        }
        return null;
    }
}
