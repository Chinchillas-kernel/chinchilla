package com.fastcampus.chinchilla.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.List;
import java.util.Map;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class AgentResponse {
    private String answer;
    private String answerHtml;
    private List<Map<String, Object>> sources;
    private Map<String, Object> metadata;
}
