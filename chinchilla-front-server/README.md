# 친칠라 프론트엔드 (elder-wise-chat)

시니어 복지/법률/일자리 상담 챗봇 서비스의 프론트엔드입니다. React + Vite + TypeScript 기반으로 개발되었으며 shadcn-ui와 Tailwind CSS를 사용해 인터페이스를 구성했습니다.

## 주요 기능

- **카테고리 기반 상담**: 일자리, 법률, 복지, 뉴스, 금융사기 등 카테고리를 선택하면 해당 RAG 에이전트와 연동하여 답변을 제공합니다.
- **마크다운 응답 표시**: 백엔드에서 전달되는 마크다운 형식의 답변을 ReactMarkdown + remark-gfm으로 렌더링합니다.
- **프로필 입력**: 일자리·법률 상담 시 필요한 프로필 정보를 수집하여 에이전트 요청에 포함합니다.
- **글꼴 크기 조절**: 상단 헤더에서 가-/가+ 버튼 또는 퍼센트 입력으로 전체 글자 크기를 조정할 수 있습니다.
- **참고 자료 표기**: 에이전트 응답에 포함된 출처 링크를 말풍선 하단에 정리해 표시합니다.

## 폴더 구조

```
chinchilla-front-server/
├─ public/            # 정적 자산 (파비콘, 이미지 등)
├─ src/
│  ├─ components/     # UI 컴포넌트 및 사이드바, 프로필 폼 등
│  ├─ hooks/          # 커스텀 훅 (예: 모바일 대응 등)
│  ├─ lib/            # API 호출 유틸 (에이전트 쿼리 등)
│  ├─ pages/          # 라우트 페이지 (Index, Chat, NotFound)
│  ├─ App.tsx         # 전역 레이아웃, 글꼴 조절, 라우팅 구성
│  ├─ main.tsx        # 루트 렌더링
│  └─ index.css       # Tailwind 및 전역 스타일
├─ package.json
├─ tsconfig*.json
├─ tailwind.config.ts
└─ README.md          # 본 파일
```

## 개발 환경 설정

> Node.js 18 이상, npm 9 이상을 권장합니다. (현 프로젝트는 npm 10 사용)

```bash
# 의존성 설치
npm install

# 개발 서버 실행 (기본 포트 5173)
npm run dev

# 타입/린트 검사 (ESLint)
npm run lint

# 프로덕션 번들 빌드
npm run build

# 빌드 결과 확인
npm run preview
```

## 환경 변수

- `VITE_API_BASE_URL`: 백엔드 RAG 서비스(FastAPI)의 베이스 URL. 기본값은 `http://localhost:8000`.

`.env` 파일 또는 실행 환경에서 설정할 수 있습니다.

## 백엔드 연동

프론트는 `/agent/query` 엔드포인트로 POST 요청을 보내 카테고리별 에이전트와 통신합니다. 필요한 경우 카테고리·프로필·히스토리 구조가 `src/lib/api.ts`에 정의되어 있으니, API 변경 시 해당 파일을 수정해주세요.

## 린트 경고

shadcn-ui 기본 템플릿에서 가져온 일부 UI 파일은 React Fast Refresh 경고(`react-refresh/only-export-components`)가 있을 수 있습니다. 기능상 문제는 없지만, 필요하면 컴포넌트를 별도 파일로 분리하거나 ESLint 설정을 조정해 경고를 제거할 수 있습니다.

## 배포 참고

- Vite 빌드 출력은 `dist/` 폴더에 생성됩니다.
- 정적 호스팅(예: Netlify, Vercel, S3) 또는 Express/Nginx와 같은 서버에서 `dist`를 서빙할 수 있습니다.
- CI/CD 파이프라인에서 `npm ci && npm run build`를 실행한 뒤 `dist`를 배포하세요.

## 기여 가이드

1. 새로운 기능이나 버그 수정을 위해 브랜치를 생성합니다.
2. `npm run lint`와 `npm run build`로 기본 체크를 통과한 뒤 커밋합니다.
3. Pull Request 생성 시 변경 요약과 테스트 결과를 함께 남겨주세요.

---

문의/건의 사항은 백엔드 저장소(`chinchilla-python-rag`) 또는 프로젝트 이슈 트래커를 통해 공유해 주세요.
