let currentUser = null;
let isTyping = false;
let currentFullText = '';
let typingInterval = null;
let happyKeywords = []; // ⭐ 백엔드에서 받아올 금지어 리스트

// 화면 전환
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showLogin() {
    showScreen('login-screen');
}

function showSignup() {
    showScreen('signup-screen');
}

function showChat() {
    showScreen('chat-screen');
}

function updateAge() {
    const age = document.getElementById('signup-age').value;
    document.getElementById('age-display').textContent = age;
}

async function signup() {
    const userId = document.getElementById('signup-id').value.trim();
    const password = document.getElementById('signup-pw').value.trim();
    const name = document.getElementById('signup-name').value.trim();
    const gender = document.getElementById('signup-gender').value;
    const age = document.getElementById('signup-age').value;
    const school = document.getElementById('signup-school').value;
    const agree = document.getElementById('agree').checked;

    if (!userId || !password || !name) {
        alert('모든 필드를 입력해주세요.');
        return;
    }
    if (!agree) {
        alert('이용약관에 동의해주세요.');
        return;
    }

    try {
        const response = await fetch('/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, password, name, gender, age: parseInt(age), school })
        });

        if (response.ok) {
            alert('회원가입 성공! 로그인해주세요.');
            showLogin();
        } else {
            const error = await response.json();
            alert(error.detail || '회원가입 실패');
        }
    } catch (error) {
        alert('서버 오류가 발생했습니다.');
    }
}

async function login() {
    const userId = document.getElementById('login-id').value.trim();
    const password = document.getElementById('login-pw').value.trim();

    if (!userId || !password) {
        alert('아이디와 비밀번호를 입력해주세요.');
        return;
    }

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, password })
        });

        if (response.ok) {
            const data = await response.json();
            currentUser = data;
            happyKeywords = data.happy_keywords || []; // ⭐ 금지어 리스트 저장
            
            showChat();
            const chatArea = document.getElementById('chat-area');
            chatArea.innerHTML = '';
            
            if (data.chat_history && data.chat_history.user_chat && data.chat_history.user_chat.length > 0) {
                for (let i = 0; i < data.chat_history.bot_chat.length; i++) {
                    if (data.chat_history.user_chat[i]) addMessage(data.chat_history.user_chat[i], 'user', false);
                    if (data.chat_history.bot_chat[i]) addMessage(data.chat_history.bot_chat[i], 'bot', false);
                }
            } else {
                showWelcome();
            }
        } else {
            const error = await response.json();
            alert(error.detail || '로그인 실패');
        }
    } catch (error) {
        alert('서버 오류가 발생했습니다.');
    }
}

async function logout() {
    if (!currentUser) return;
    try {
        await fetch('/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.user_id })
        });
    } catch (error) {
        console.error('로그아웃 오류:', error);
    }
    currentUser = null;
    happyKeywords = [];
    document.getElementById('login-id').value = '';
    document.getElementById('login-pw').value = '';
    showLogin();
}

function showWelcome() {
    const welcomeMsg = `${currentUser.name}님, 환영합니다! 진로 고민을 해결하는 마법사, CareerMate입니다. 요즘 어떤 것에 관심이 있나요? 다음과 같이 말해보세요.\n1. 관심사를 말해보세요. 예) '나는 영화를 좋아해.'\n2. 궁금한 직업에 대해 물어보세요. 요리사, 축구 선수, 아나운서 같은 여러 직업을 알려드릴 수 있어요.`;
    addMessage(welcomeMsg, 'bot', true);
}

async function clearChat() {
    if (!confirm('지금까지의 대화 내용을 모두 삭제하시겠습니까?')) return;
    try {
        await fetch('/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.user_id })
        });
        document.getElementById('chat-area').innerHTML = '';
        addMessage('대화가 초기화되었습니다. 새로운 이야기를 시작해보세요!', 'bot', true);
    } catch (error) {
        alert('채팅 초기화 실패');
    }
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    if (!message || isTyping) return;

    input.value = '';
    addMessage(message, 'user', false);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.user_id, message })
        });

        if (response.ok) {
            const data = await response.json();
            typeMessage(data.response);
        } else {
            addMessage('오류가 발생했습니다.', 'bot', false);
        }
    } catch (error) {
        addMessage('서버 연결에 실패했습니다.', 'bot', false);
    }
}

// ⭐ 핵심 수정: 타이핑 중 금지어 감지 로직 적용
// ⭐ 핵심 수정: 타이핑 중 금지어 감지 로직 적용
function typeMessage(text) {
    isTyping = true;
    currentFullText = text;
    // ▼▼▼ skip-btn 관련 코드 완전 제거 ▼▼▼
    
    let index = 0;
    const chatArea = document.getElementById('chat-area');
    
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    
    const senderDiv = document.createElement('div');
    senderDiv.className = 'message-sender';
    senderDiv.textContent = 'CareerMate';
    msgDiv.appendChild(senderDiv);
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    msgDiv.appendChild(contentDiv);
    
    chatArea.appendChild(msgDiv);
    chatArea.scrollTop = chatArea.scrollHeight;

    typingInterval = setInterval(() => {
        if (index < currentFullText.length) {
            contentDiv.textContent += currentFullText[index];
            
            // ⭐ 실시간 금지어(happy) 감지
            const currentText = contentDiv.textContent;
            const isBanned = happyKeywords.some(word => currentText.includes(word));
            
            if (isBanned) {
                clearInterval(typingInterval); // 타이핑 즉시 중단
                isTyping = false;
                
                msgDiv.remove(); // 방금 출력하던 메시지 전체 삭제
                
                // 새 경고 메시지 출력
                typeMessage("미안, 그건 답할 수 없어.");
                return;
            }
            
            index++;
            chatArea.scrollTop = chatArea.scrollHeight;
        } else {
            clearInterval(typingInterval);
            isTyping = false;
        }
    }, 30);
}

function addMessage(text, sender, isWelcome = false) {
    const chatArea = document.getElementById('chat-area');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    
    if (!isWelcome) {
        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.textContent = sender === 'user' ? (currentUser ? currentUser.name : '나') : 'CareerMate';
        msgDiv.appendChild(senderDiv);
    }
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = text.replace(/\n/g, '<br>');
    msgDiv.appendChild(contentDiv);
    
    chatArea.appendChild(msgDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
}


function handleKeyPress(event) {
    if (event.key === 'Enter') sendMessage();
}

document.addEventListener('DOMContentLoaded', () => {
    showLogin();
});