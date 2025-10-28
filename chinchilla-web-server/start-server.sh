#!/bin/bash

echo "🐳 Starting Docker Compose services..."
docker compose up -d

echo "⏳ Waiting for services to be ready..."
echo "   - Waiting for MySQL..."
until docker compose exec -T mysql mysqladmin ping -h localhost -uroot -proot1234 --silent 2>/dev/null; do
    echo "   - MySQL is still starting..."
    sleep 2
done
echo "   ✅ MySQL is ready!"

echo "   - Waiting for ChromaDB..."
sleep 3  # ChromaDB는 빠르게 시작되므로 3초 대기
until curl -s http://localhost:8001/api/v1 >/dev/null 2>&1; do
    echo "   - ChromaDB is still starting..."
    sleep 2
done
echo "   ✅ ChromaDB is ready!"

echo ""
echo "✅ All Docker services are ready!"
echo "   - MySQL: localhost:3307"
echo "   - ChromaDB: http://localhost:8001"
echo ""
echo "🚀 Starting Spring Boot application..."
./gradlew bootRun