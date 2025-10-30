package com.fastcampus.chinchilla.dto;

public class AgentRequest {
    private String category;
    private Object payload;

    public AgentRequest() {}

    public AgentRequest(String category, Object payload) {
        this.category = category;
        this.payload = payload;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public Object getPayload() {
        return payload;
    }

    public void setPayload(Object payload) {
        this.payload = payload;
    }
}
