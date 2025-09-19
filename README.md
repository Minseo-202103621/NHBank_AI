# 🚨 Bank Whistle AI

**은행권 내부고발 AI 시스템 (PoC)**

---

## 📌 개요
Bank Whistle AI는 **은행 내부 제보 시스템**의 프로토타입으로, 대화형 AI 챗봇을 통해 내부고발 상담 및 접수를 처리합니다.
익명성이 보장되는 채팅 환경에서 사용자는 파일 증거를 제출하고, AI는 내부 규정 및 문서를 실시간으로 참조하여 답변과 분석을 제공합니다.
최종적으로 AI는 접수된 내용을 바탕으로 **배임, 횡령, 불완전판매, 개인정보 유출** 등과 관련된 위반 가능성을 분석하고, 판정 보고서를 생성합니다.

---

## ⚙️ 주요 기능
- **대화형 익명 상담 및 제보**
  - 웹 기반 채팅 인터페이스를 통해 익명으로 AI 상담사와 대화
  - 증거 자료(PDF, 이미지 등)를 채팅으로 안전하게 업로드
- **규정 기반 답변 생성 (RAG)**
  - `ChromaDB` 벡터 저장소를 활용하여 내부 규정 및 문서를 실시간으로 검색
  - 사용자의 질문 의도에 맞는 가장 관련성 높은 규정 내용을 찾아 답변에 근거로 활용
- **AI 자동 판정 (LLM-as-a-Judge)**
  - 대화 내용과 제출된 증거를 종합하여 OpenAI `gpt-4o` 모델이 위반 유형, 심각도, 권고 조치 등을 포함한 최종 판정 생성
- **감사 및 추적**
  - 모든 대화 내용과 판정 결과는 데이터베이스에 저장되어 추후 검증 및 감사에 활용

---

## 🚀 실행 방법

### 1. 환경 변수 설정
```bash
cp .env.example .env
.env 파일을 열고 OPENAI_API_KEY 값을 입력하세요.

2. 의존성 설치

**권장 Python 버전: 3.11**

```bash
pip install -r requirements.txt
3. 규정 인덱스 생성
data/ 폴더 안에 분석할 내부 규정 PDF 파일들을 위치시킵니다.

bash
python -m scripts.build_index data/ --output data/regulation_index.jsonl
위 명령어를 실행하면 data/regulation_index.jsonl 파일이 생성됩니다.

4. 서버 및 프론트엔드 실행
백엔드 서버 실행:

bash
uvicorn app.main:app --reload
서버가 시작되면 storage/chroma 디렉터리에 벡터 인덱스가 자동으로 생성 또는 로드됩니다. 기본 API 주소: http://localhost:8000/docs

프론트엔드 개발 서버 실행:

bash
cd frontend
npm install
npm run dev
웹 브라우저에서 http://localhost:5173으로 접속하여 챗봇 서비스를 이용할 수 있습니다.

📝 판정 결과 예시
AI 판정 요청 시, 백엔드는 다음과 같은 JSON 형식의 응답을 반환합니다.

json
 Show full code block 
 {
   "violation_type": ["배임/횡령"],
   "severity": 2,
   "severity_label": "배임 횡령(조사 필요)",
   "recommended_actions": ["내부 감사 착수"],
   "rationale": "무단 자금 이동 정황. 규정 §12조 위반 소지.",
   "policy_links": "[{\"title\":\"금융소비자 보호에 관한 법률\",\"url\":\"...\"}]"
 }
📂 프로젝트 구조
plaintext
 Show full code block 
bank_whistle_ai/
├─ app/                # FastAPI 엔트리포인트 및 스키마
├─ agent/              # 대화 관리 및 LLM 오케스트레이션 로직
├─ judge/              # LLM 판정을 위한 프롬프트 및 관련 유틸리티
├─ retriever/          # 규정 인덱싱 및 벡터 검색 (RAG)
├─ storage/            # DB 모델, ChromaDB 영구 저장소
├─ policy/             # 루브릭 및 용어사전
├─ scripts/            # 인덱스 빌드 등 유틸리티 스크립트
├─ data/               # 원본 규정 PDF 및 생성된 JSONL 인덱스 파일
└─ frontend/           # React 기반 웹 프론트엔드


