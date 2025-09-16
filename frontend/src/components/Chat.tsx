import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Modal, Button, ButtonGroup } from 'react-bootstrap';
import './Chat.css';
import nhLogo from '../assets/nh_logo.png';
import attachLogo from '../assets/attach_logo.png';

// 메시지 타입을 정의합니다.
interface Message {
  sender: 'bot' | 'user';
  text: string;
}

// API 응답 타입을 정의합니다.
interface JudgeResponse {
  violation_type: string[];
  severity: number;
  severity_label: string;
  recommended_actions: string[];
  rationale: string;
  policy_links: string; // JSON string
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isReadyForJudgment, setIsReadyForJudgment] = useState(false);

  // --- Modals State ---
  const [showSettings, setShowSettings] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [theme, setTheme] = useState('green');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement | null>(null);

  // 메시지 목록이 업데이트될 때마다 맨 아래로 스크롤합니다.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startChat = async () => {
    setIsTyping(true);
    try {
      const response = await axios.post('http://localhost:8000/chat/start');
      const { conversation_id, message } = response.data;
      setConversationId(conversation_id);
      setMessages([{ sender: 'bot', text: message }]);
    } catch (error) {
      setMessages([{ sender: 'bot', text: '오류: 대화를 시작하지 못했습니다.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  // 컴포넌트가 마운트될 때 대화를 시작합니다.
  useEffect(() => {
    startChat();
  }, []);

  const handleSendMessage = async () => {
    const currentInput = input.trim();
    if (!currentInput || !conversationId || isTyping) return;

    const userMessage: Message = { sender: 'user', text: currentInput };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    requestAnimationFrame(() => {
        const ta = scrollAreaRef.current?.querySelector<HTMLTextAreaElement>(".draft-input");
        if (ta) { 
            ta.style.height = "auto";
            ta.style.height = "44px";
        }
    });

    setIsTyping(true);

    try {
        if (isReadyForJudgment && (currentInput.toLowerCase() === '예' || currentInput.toLowerCase() === 'yes')) {
            await handleJudge();
            return; 
        }

      const response = await axios.post('http://localhost:8000/chat/message', {
        conversation_id: conversationId,
        message: currentInput,
      });
      
      const { message: botMessage, ready_for_judgment } = response.data;
      setMessages(prev => [...prev, { sender: 'bot', text: botMessage }]);
      
      if (ready_for_judgment) {
        setIsReadyForJudgment(true);
        setMessages(prev => [...prev, { sender: 'bot', text: '최종적으로 제보 내용을 바탕으로 판정을 진행할까요? (예/아니오)' }]);
      }

    } catch (error) {
      setMessages(prev => [...prev, { sender: 'bot', text: '오류: 메시지를 처리하지 못했습니다.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0 && conversationId) {
      const file = event.target.files[0];
      const formData = new FormData();
      formData.append('conversation_id', conversationId);
      formData.append('file', file);

      const uploadMessage: Message = { sender: 'user', text: `파일 업로드 중: ${file.name}` };
      setMessages(prev => [...prev, uploadMessage]);
      setIsTyping(true);

      try {
        await axios.post('http://localhost:8000/chat/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        const confirmationMessage = `파일이 성공적으로 업로드되었습니다: ${file.name}. AI가 파일 내용을 확인하고 있습니다.`;
        setMessages(prev => [...prev, { sender: 'bot', text: confirmationMessage }]);

      } catch (error) {
        setMessages(prev => [...prev, { sender: 'bot', text: `오류: ${file.name} 파일을 업로드하지 못했습니다.` }]);
      } finally {
        setIsTyping(false);
        if(fileInputRef.current) {
            fileInputRef.current.value = '';
        }
      }
    }
  };

  const handleJudge = async () => {
    if (!conversationId) return;
    setIsTyping(true);
    try {
      const response = await axios.post<JudgeResponse>(`http://localhost:8000/chat/judge`,
 {
          conversation_id: conversationId,
          message: "판정을 요청합니다."
      });
      const result = response.data;
      let policyLinksText = '';
      try {
          const links = JSON.parse(result.policy_links || '[]');
          if(Array.isArray(links) && links.length > 0){
              policyLinksText = `
- **관련 규정:**
${links.map(link => `  - [${link.title}](${link.url})`).join('\n')}`;
          }
      } catch(e) {
          console.error("Failed to parse policy_links", e);
      }

      const resultText = `
        **AI 판정 결과:**
        - **위반 유형:** ${result.violation_type.join(', ')}
        - **심각도:** ${result.severity_label}
        - **판단 근거:** ${result.rationale}
        - **권고 조치:** ${result.recommended_actions.join(', ')}
        ${policyLinksText}
      `;

      setMessages(prev => [...prev, { sender: 'bot', text: resultText }]);
      setIsReadyForJudgment(false);
    } catch (error) {
      setMessages(prev => [...prev, { sender: 'bot', text: '오류: AI 판정을 진행하지 못했습니다.' }]);
    } finally {
        setIsTyping(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setInput('');
    setIsReadyForJudgment(false);
    startChat();
  }

  const autoGrow = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 220) + "px";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // --- Modal Handlers ---
  const handleShowSettings = () => setShowSettings(true);
  const handleCloseSettings = () => setShowSettings(false);
  const handleClearChat = () => {
    setMessages([]);
    handleCloseSettings();
  };
  const handleShowHelp = () => setShowHelp(true);
  const handleCloseHelp = () => setShowHelp(false);

  return (
    <div className={`page-container theme-${theme}`}>
      {/* Background */}
      <div className="app-bg" />
      <div className="app-grid" />
      <div className="app-fade-bottom" />

      {/* Topbar (glass) */}
      <div className="topbar d-flex align-items-center justify-content-between">
        <div className="d-flex align-items-center gap-2">
          <img src={nhLogo} alt="Bank Whistle AI Logo" style={{ width: 40, height: 40, position: 'relative', top: '-2px' }} />
          <span className="bold">Bank Whistle AI</span>
        </div>

        <button className="btn-primary" onClick={handleNewChat}>New Chat</button>
      </div>

      {/* Layout */}
      <div className="chat-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <button className="nav-btn">
            <span style={{ display: "inline-block", width: 10, height: 10, background: "var(--g-700)", borderRadius: 999, marginRight: 8 }} />
            AI Chat Helper
          </button>

          <div className="hr"></div>

          <div className="text-sm bold" style={{ color: "#6b6b6b" }}>Recents</div>
          <ul className="recents" style={{ margin: "8px 0 0 0", padding: 0 }}>
            <li>내부지침 문의 요약</li>
            <li>부서배치 관련 상담</li>
            <li>익명성 보장 정책</li>
            <li>신고접수 절차</li>
          </ul>

          <div className="hr"></div>
          <button className="nav-btn" onClick={handleShowSettings}>⚙️ Settings</button>
          <button className="nav-btn" onClick={handleShowHelp}>❓ Help</button>
        </aside>

        {/* Main */}
        <main className="main-card">
          {/* Header row inside card */}
          <div className="d-flex align-items-center justify-content-between">
            <div className="d-flex align-items-center gap-3">
               <img src={nhLogo} alt="Bank Whistle AI Logo" style={{ width: 44, height: 40 }} />
              <div className="text-sm">
                <div className="bold">Bank Whistle AI</div>
                <div style={{ color: "#6b6b6b" }}>NH 환경에 맞춘 안전한 내부고발 상담</div>
              </div>
            </div>
            <button className="btn-primary" style={{ padding: "6px 10px" }} onClick={handleNewChat}>+ New Chat</button>
          </div>

          {/* 메시지 스크롤 영역 */}
          <div className="chat-body" ref={scrollAreaRef}>
            {messages.map((m, i) => (
              <div key={i} className={`msg-row ${m.sender}`}>
                <div className={`bubble ${m.sender}`}>
                   {m.sender === 'bot' ? (
                      <span dangerouslySetInnerHTML={{ __html: m.text.replace(/\n/g, '<br />') }} />
                    ) : (
                      m.text
                    )}
                </div>
              </div>
            ))}

            {isTyping && (
                <div className="msg-row bot">
                    <div className="bubble bot">...</div>
                </div>
            )}

            {/* === 인라인 입력창(오른쪽 버블) === */}
            <div className="draft-row">
              <div className="draft-bubble">
                <div className="draft-col">
                  <textarea
                    className="draft-input"
                    placeholder="메시지를 입력하세요… (개인식별 정보는 적지 마세요)"
                    value={input}
                    onChange={(e) => {
                      setInput(e.target.value);
                      autoGrow(e.target);
                    }}
                    onKeyDown={handleKeyDown}
                    rows={1}
                  />
                  <div className="draft-toolbar">
                    <label className="attach">
                      <input type="file" hidden onChange={handleFileUpload} ref={fileInputRef}/>
                      <img src={attachLogo} alt="Attach" style={{ width: '16px', height: '16px', marginRight: '4px' }} /> Attach
                    </label>
                  </div>
                </div>

                <button className="send-btn" onClick={handleSendMessage} aria-label="Send" disabled={isTyping}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
                    <path d="M2 21l20-9L2 3v7l15 2-15 2v7z" />
                  </svg>
                </button>
              </div>
            </div>

            <div ref={endRef} />
          </div>
        </main>
      </div>

      {/* Settings Modal */}
      <Modal show={showSettings} onHide={handleCloseSettings} centered>
        <Modal.Header closeButton>
          <Modal.Title>Settings</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <h5>테마 색상</h5>
          <ButtonGroup className="mb-3">
            <Button variant={theme === 'green' ? 'success' : 'outline-success'} onClick={() => setTheme('green')}>Green</Button>
            <Button variant={theme === 'blue' ? 'primary' : 'outline-primary'} onClick={() => setTheme('blue')}>Blue</Button>
          </ButtonGroup>
          
          <hr />

          <h5>대화 관리</h5>
          <Button variant="danger" onClick={handleClearChat}>대화 내용 모두 지우기</Button>

        </Modal.Body>
      </Modal>

      {/* Help Modal */}
      <Modal show={showHelp} onHide={handleCloseHelp} centered>
        <Modal.Header closeButton>
          <Modal.Title>도움말</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <h5>메시지 입력</h5>
          <p>메시지 입력 후 `Enter` 키를 누르면 전송됩니다. 줄바꿈을 하시려면 `Shift` + `Enter`를 입력하세요.</p>
          
          <hr />

          <h5>파일 첨부</h5>
          <p>입력창 하단의 'Attach' 버튼을 눌러 분석할 파일을 첨부할 수 있습니다. 파일의 내용을 바탕으로 AI와 대화할 수 있습니다.</p>

          <hr />

          <h5>설정</h5>
          <p>사이드바의 'Settings' 버튼을 눌러 앱의 테마 색상을 변경하거나, 현재 대화 내용을 모두 지울 수 있습니다.</p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseHelp}>
            닫기
          </Button>
        </Modal.Footer>
      </Modal>

    </div>
  );
};

export default Chat;