package com.fastcampus.chinchilla.dto;

import java.util.List;
import java.util.Map;

public class AgentResponse {
    private String answer;
    private List<Map<String, Object>> sources;
    private Map<String, Object> metadata;

    public AgentResponse() {}

    public String getAnswer() {
        return answer;
    }

    public void setAnswer(String answer) {
        this.answer = answer;
    }

    public List<Map<String, Object>> getSources() {
        return sources;
    }

    public void setSources(List<Map<String, Object>> sources) {
        this.sources = sources;
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }
}
