from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import backend_logic as logic
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# 요청 모델
class LoginRequest(BaseModel):
    user_id: str
    password: str

class SignupRequest(BaseModel):
    user_id: str
    password: str
    name: str
    gender: str
    age: int
    school: str

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/signup")
async def signup(request: SignupRequest):
    result = logic.check_user(request.user_id, request.password)
    if result == 'already':
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    elif result == 'special_banned':
        raise HTTPException(status_code=400, detail="아이디에 특수문자를 포함할 수 없습니다.")
    
    logic.save_initial_data(
        request.user_id, request.password, request.name,
        request.gender, request.age, request.school
    )
    logic.config_chat_data(request.user_id, '', 'initial')
    return {"message": "회원가입 성공", "user_id": request.user_id, "name": request.name}

@app.post("/login")
async def login(request: LoginRequest):
    success = logic.login_(request.user_id, request.password)
    if not success:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.")
    
    session = logic.get_session(request.user_id)
    chat_history = logic.get_chat_history(request.user_id)
    return {
        "message": "로그인 성공",
        "user_id": request.user_id,
        "name": session.get('name', ''),
        "chat_history": chat_history,
        "happy_keywords": logic.datas.get('happy', [])
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    session = logic.get_session(request.user_id)
    user_name = session.get('name', '사용자')
    
    logic.detect_topic(request.message, session)
    
    if session['chat_topic'] == 'ban':
        return {"response": f"{user_name} 친구, 그런 말은 사용하면 안돼요.", "topic": ""}
    
    if session['last_topic']:
        analyze_result = logic.analyze_followings(request.message, session)
        if analyze_result:
            answer = ''
            if session['last_topic'] == 'hobby_detail':
                answer = logic.handle_hobby(request.message, user_name, session, user_react=analyze_result)
            elif session['last_topic'] == 'greeting' and analyze_result == 're_greeting':
                answer = logic.handle_greeting(request.message, user_name, session, re_greeting=analyze_result)
            elif session['last_topic'] in ['hobby_to_career', 'career_suggest', 'career_merit']:
                answer = logic.handle_career(request.message, session, user_react=analyze_result)
            
            if answer:
                logic.config_chat_data(request.user_id, request.message, 'user_chat')
                logic.config_chat_data(request.user_id, answer, 'bot_chat')
                session['chat_topic'] = ''
                return {"response": answer, "topic": session['chat_topic']}
    
    answer = ''
    if session['chat_topic'] == 'career' or session['last_topic'] == 'career_merit':
        answer = logic.handle_career(request.message, session)
    elif session['chat_topic'] == 'greeting':
        answer = logic.handle_greeting(request.message, user_name, session)
    elif session['chat_topic'] == 'hobby':
        answer = logic.handle_hobby(request.message, user_name, session)
    
    if not answer:
        answer = f'''{user_name}, 안녕하세요? 저는 학생분의 진로 고민을 도와주는 챗봇 비서예요. 이 질문은 제 역할이 아닌 것 같아요. 대신에 이렇게 말씀하시면 도와드릴 수 있어요.
1. 관심사를 말해보세요. 예) '나는 영화를 좋아해.'
2. 궁금한 직업에 대해 물어보세요. 요리사, 축구 선수, 아나운서 같은 여러 직업을 알려드릴 수 있어요.'''
    
    logic.config_chat_data(request.user_id, request.message, 'user_chat')
    logic.config_chat_data(request.user_id, answer, 'bot_chat')
    session['chat_topic'] = ''
    return {"response": answer, "topic": session['chat_topic']}

@app.post("/clear")
async def clear_chat(request: dict):
    user_id = request.get('user_id')
    if user_id:
        logic.clear_chat_history(user_id)
        return {"message": "채팅 초기화 완료"}
    raise HTTPException(status_code=400, detail="user_id가 필요합니다.")

@app.post("/logout")
async def logout(request: dict):
    user_id = request.get('user_id')
    if user_id and user_id in logic.user_sessions:
        del logic.user_sessions[user_id]
        return {"message": "로그아웃 완료"}
    raise HTTPException(status_code=400, detail="user_id가 필요합니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)