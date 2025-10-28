# 웹서버 실행 시 Docker 자동 시작 설정 완료

## 설정된 기능

Spring Boot 3.5.7의 **공식 Docker Compose 지원**을 활성화했습니다.

## 변경 사항

### 1. build.gradle
```gradle
dependencies {
    developmentOnly 'org.springframework.boot:spring-boot-docker-compose'
}
```

### 2. application.yml
```yaml
spring:
  docker:
    compose:
      enabled: true
      file: docker-compose.yml
      lifecycle-management: start-and-stop
      start:
        command: up
      stop:
        command: stop
      readiness:
        wait: always
        timeout: 5m
```

## 사용 방법

### 이제 그냥 웹서버를 실행하세요!

```bash
./gradlew bootRun
```

또는 IntelliJ IDEA에서 Run 버튼 클릭

## 자동으로 일어나는 일

1. Spring Boot 시작
2. `docker-compose.yml` 감지
3. MySQL과 ChromaDB 자동 시작
4. 서비스 준비 완료 대기
5. 웹서버 시작
6. 웹서버 종료 시 Docker 서비스도 자동 중지

## 로그 예시

```
.s.b.d.c.l.DockerComposeLifecycleManager : Using Docker Compose file /path/to/docker-compose.yml
 Network chinchilla-web-server_default  Creating
 Container chinchilla-mysql  Creating
 Container chinchilla-chromadb  Creating
 Container chinchilla-mysql  Started
 Container chinchilla-chromadb  Started
HikariPool-1 - Starting...
HikariPool-1 - Start completed.
Tomcat started on port 8080
```

## 서비스 정보

| 서비스 | 포트 | 접속 URL |
|--------|------|----------|
| MySQL | 3307 | `jdbc:mysql://localhost:3307/chinchilla` |
| ChromaDB | 8001 | `http://localhost:8001` |
| Web Server | 8080 | `http://localhost:8080` |

## 추가 설정 옵션

### 프로덕션 환경에서 비활성화

`application-prod.yml`:
```yaml
spring:
  docker:
    compose:
      enabled: false
```

### 다른 compose 파일 사용

```yaml
spring:
  docker:
    compose:
      file: docker-compose-custom.yml
```

### 종료 시 컨테이너 삭제

```yaml
spring:
  docker:
    compose:
      stop:
        command: down
```

## 참고 자료

- [Spring Boot Docker Compose 공식 문서](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.docker-compose)
- 프로젝트: `build.gradle`, `application.yml`, `docker-compose.yml`
