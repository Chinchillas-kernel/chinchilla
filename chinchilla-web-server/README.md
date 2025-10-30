# 노인 행정도우미 챗봇 - Spring Web Server

## 프로젝트 구조

```
src/
├── main/
│   ├── java/com/fastcampus/chinchilla/
│   │   ├── controller/
│   │   │   ├── AgentController.java      # 페이지 라우팅
│   │   │   └── AgentRestController.java  # REST API
│   │   ├── dto/
│   │   │   ├── AgentRequest.java        # API 요청 DTO
│   │   │   ├── AgentResponse.java       # API 응답 DTO
│   │   │   ├── JobQueryPayload.java     # 일자리 매칭 페이로드
│   │   │   └── UserProfile.java         # 사용자 프로필
│   │   ├── config/
│   │   │   └── RestTemplateConfig.java  # RestTemplate 설정
│   │   └── exception/
│   │       └── GlobalExceptionHandler.java # 전역 예외 처리
│   └── resources/
│       ├── templates/
│       │   ├── main.html                # 메인 페이지 (카테고리 선택)
│       │   └── chat.html                # 채팅 페이지
│       ├── static/css/
│       │   └── style.css               # 추가 스타일시트
│       └── application.yml             # 설정 파일
```

## 주요 기능

### 1. 메인 페이지 (`/`)
- 5개 카테고리 선택 화면
  - 일자리 매칭 (jobs)
  - 건강 정보 (health)
  - 복지 혜택 (welfare)
  - 취미/여가 (hobby)
  - 교육/학습 (education)

### 2. 채팅 페이지 (`/chat/{category}`)
- 카테고리별 맞춤형 채팅 인터페이스
- 일자리 매칭의 경우:
  - 왼쪽에 프로필 입력 폼 (나이, 성별, 거주지)
  - 프로필 정보와 함께 질의 전송

### 3. API 엔드포인트
- `POST /api/chat` - 챗봇과 대화

#### 일자리 매칭 요청 예시:
```json
{
  "category": "jobs",
  "query": "무릎이 안 좋은데 할 수 있는 일자리 추천해주세요",
  "age": 65,
  "gender": "male",
  "location": "강남구"
}
```

## 실행 방법

1. Python FastAPI 서버 실행 (포트 8000)
```bash
cd ../chinchilla-python-rag/python_service
python main.py
```

2. Spring Boot 애플리케이션 실행
```bash
./mvnw spring-boot:run
```

3. 브라우저에서 접속
```
http://localhost:8080
```

## 설정

`application.yml`에서 Python RAG 서버 URL 설정:
```yaml
agent:
  api:
    url: http://localhost:8000  # Python FastAPI 서버 주소
```

## 화면 구성

### 메인 화면
- 복지로 챗봇 소개
- 사용 팁 안내
- 5개 카테고리 카드형 버튼

### 채팅 화면
- 상단: 헤더 (뒤로가기, 제목)
- 좌측: 프로필 입력 폼 (일자리 매칭 전용)
- 중앙: 채팅 메시지 영역
- 하단: 메시지 입력창

## 주요 특징

1. **반응형 디자인**: 모바일에서도 사용 가능
2. **실시간 대화**: 비동기 통신으로 빠른 응답
3. **타이핑 인디케이터**: 응답 대기 중 표시
4. **에러 처리**: 서비스 장애 시 친절한 안내 메시지

## 향후 개선사항

1. 세션 관리: 대화 내용 저장 및 불러오기
2. 파일 업로드: 서류 첨부 기능
3. 음성 인터페이스: STT/TTS 기능
4. 다국어 지원: 영어, 중국어 등
