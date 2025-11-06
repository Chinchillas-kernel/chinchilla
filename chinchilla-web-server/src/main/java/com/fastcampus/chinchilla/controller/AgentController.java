package com.fastcampus.chinchilla.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

@Controller
public class AgentController {

    @GetMapping("/")
    public String mainPage(Model model) {
        // 카테고리 목록을 모델에 추가
        model.addAttribute("categories", new String[]{
            "jobs", // 일자리 매칭
            "health", // 건강 정보
            "welfare", // 복지 혜택
            "hobby", // 취미/여가
            "education", // 교육/학습
            "scam_defense" // 금융 사기 탐지
        });
        return "main";
    }

    @GetMapping("/chat/{category}")
    public String chatPage(@PathVariable String category, Model model) {
        model.addAttribute("category", category);
        
        // 카테고리별 제목 설정
        String categoryTitle = switch (category) {
            case "jobs" -> "일자리 매칭";
            case "health" -> "건강 정보";
            case "welfare" -> "복지 혜택";
            case "hobby" -> "취미/여가";
            case "education" -> "교육/학습";
            case "scam_defense" -> "금융 사기 탐지";
            default -> "상담";
        };
        model.addAttribute("categoryTitle", categoryTitle);
        
        return "chat";
    }
}
