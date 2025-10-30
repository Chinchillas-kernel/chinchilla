package com.fastcampus.chinchilla.dto;

public class JobQueryPayload {
    private String query;
    private UserProfile profile;

    public JobQueryPayload() {}

    public JobQueryPayload(String query, UserProfile profile) {
        this.query = query;
        this.profile = profile;
    }

    public String getQuery() {
        return query;
    }

    public void setQuery(String query) {
        this.query = query;
    }

    public UserProfile getProfile() {
        return profile;
    }

    public void setProfile(UserProfile profile) {
        this.profile = profile;
    }
}
