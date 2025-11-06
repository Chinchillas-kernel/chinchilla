package com.fastcampus.chinchilla.config;

import org.commonmark.node.Node;
import org.commonmark.parser.Parser;
import org.commonmark.renderer.html.HtmlRenderer;
import org.springframework.stereotype.Component;

@Component
public class CommonUtil {
    private final Parser parser = Parser.builder().build();
    private final HtmlRenderer renderer = HtmlRenderer.builder()
            .escapeHtml(true)    // 입력에 들어온 원시 HTML은 이스케이프 (XSS 방지)
            .build();

    public String markdown(String markdown) {
        if (markdown == null) return "";
        Node tree = parser.parse(markdown);
        return renderer.render(tree);
    }
}
