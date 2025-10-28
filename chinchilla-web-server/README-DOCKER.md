# Chinchilla Web Server - Docker 자동 실행 가이드

## ✅ 해결 완료!

**Spring Boot 3.1+의 공식 Docker Compose 지원 기능**을 활성화했습니다.

이제 웹서버를 실행하면 **자동으로 MySQL과 ChromaDB가 시작**됩니다!

### 작동 방식

1. Spring Boot 애플리케이션 시작
2. `docker-compose.yml` 자동 감지
3. Docker Compose 서비스 자동 시작 (MySQL, ChromaDB)
4. 서비스가 준비될 때까지 자동 대기
5. 애플리케이션 종료 시 Docker 서비스 자동 중지

## 실행 방법

### 방법 1: Gradle 실행 (권장)

```bash
./gradlew bootRun
```

**자동으로 Docker Compose가 시작됩니다!**

### 방법 2: IntelliJ IDEA Run 버튼

IDE에서 Run 버튼 클릭 또는 `ChinchillaWebSeverApplication` 직접 실행

**자동으로 Docker Compose가 시작됩니다!**

### 방법 3: 터미널 스크립트 (선택사항)

```bash
./start-server.sh
```

스크립트 방식으로 명시적인 대기 로직이 필요한 경우 사용

## 서비스 정보

| 서비스 | 호스트 포트 | 컨테이너 포트 | 접속 정보 |
|--------|------------|--------------|----------|
| MySQL | 3307 | 3306 | `localhost:3307`<br>user: `root`<br>password: `root1234`<br>database: `chinchilla` |
| ChromaDB | 8001 | 8000 | `http://localhost:8001` |

## Docker 명령어

```bash
# 모든 서비스 시작
docker compose up -d

# 특정 서비스만 시작
docker compose up -d mysql
docker compose up -d chromadb

# 서비스 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f

# 서비스 중지
docker compose stop

# 서비스 중지 및 제거
docker compose down

# 볼륨까지 제거 (데이터 삭제)
docker compose down -v
```

## Gradle Docker 태스크

`build.gradle`에 정의된 커스텀 태스크:

```bash
# Docker Compose 서비스 시작
./gradlew dockerComposeUp

# Docker Compose 서비스 중지
./gradlew dockerComposeDown

# Docker Compose 서비스 상태 확인
./gradlew dockerComposeStatus
```

## 트러블슈팅

### 포트가 이미 사용 중인 경우

```bash
# 포트 사용 확인
lsof -i :3307  # MySQL
lsof -i :8001  # ChromaDB

# 해당 프로세스 종료 후 재시작
docker compose down
docker compose up -d
```

### 데이터 초기화가 필요한 경우

```bash
# 모든 컨테이너와 볼륨 제거
docker compose down -v

# 다시 시작
docker compose up -d
```

### MySQL 연결 실패

```bash
# MySQL이 완전히 준비될 때까지 대기
docker compose exec mysql mysqladmin ping -h localhost -uroot -proot1234
```

### ChromaDB 연결 확인

```bash
# ChromaDB API 테스트
curl http://localhost:8001/api/v1
```

## 데이터 영속성

데이터는 Docker 볼륨에 저장되어 컨테이너를 재시작해도 유지됩니다:

- `mysql_data`: MySQL 데이터
- `chroma_data`: ChromaDB 데이터

볼륨 확인:
```bash
docker volume ls | grep chinchilla
```
