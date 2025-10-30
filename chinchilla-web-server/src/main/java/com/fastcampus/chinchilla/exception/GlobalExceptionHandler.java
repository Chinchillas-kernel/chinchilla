package com.fastcampus.chinchilla.exception;

import com.fastcampus.chinchilla.dto.AgentResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.RestClientException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(RestClientException.class)
    public ResponseEntity<AgentResponse> handleRestClientException(RestClientException e) {
        AgentResponse errorResponse = new AgentResponse();
        errorResponse.setAnswer("죄송합니다. AI 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.");
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(errorResponse);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<AgentResponse> handleGenericException(Exception e) {
        AgentResponse errorResponse = new AgentResponse();
        errorResponse.setAnswer("죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
    }
}
