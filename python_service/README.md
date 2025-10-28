## Conda 가상환경 만들기 · 실행 방법 · 패키지 설치
아래 명령어를 순차적으로 입력하시면 됩니다.

1.	가상환경 생성(처음 1회)
(1) Python3.11 기반 Conda 환경 생성
conda create -n chinchilla-py311 python=3.11 -y
(2) 활성화
conda activate chinchilla-py311

2. 패키지 설치 (처음 1회 또는, requirements.txt 변경 시)
(1) 설치 도구 최신화
pip install -U pip setuptools wheel
(2) 프로젝트 의존성 설치
pip install -r requirements.txt --prefer-binary

3. 실행 방법
(1) 가상환경 활성화
conda activate chinchilla-py311

4. VS Code 인터프리터 선택(선택)
(1) Command Palette → “Python: Select Interpreter”
(2) conda (chinchilla-py311) 선택

5. 자주 쓰는 명령
(1) 비활성화: conda deactivate
(2) 환경 목록: conda info --envs
(3) 파이썬/패키지 버전 확인: