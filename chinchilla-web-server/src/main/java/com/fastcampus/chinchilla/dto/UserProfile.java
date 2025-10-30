package com.fastcampus.chinchilla.dto;

public class UserProfile {
    private int age;
    private String gender;
    private String location;

    public UserProfile() {}

    public UserProfile(int age, String gender, String location) {
        this.age = age;
        this.gender = gender;
        this.location = location;
    }

    public int getAge() {
        return age;
    }

    public void setAge(int age) {
        this.age = age;
    }

    public String getGender() {
        return gender;
    }

    public void setGender(String gender) {
        this.gender = gender;
    }

    public String getLocation() {
        return location;
    }

    public void setLocation(String location) {
        this.location = location;
    }
}
