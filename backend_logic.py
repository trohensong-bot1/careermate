import random as r
import os
import json
from openai import OpenAI
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
# DeepSeek API 클라이언트
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,  # 실제 API 키로 변경
    base_url="https://api.deepseek.com"
)

# 전역 변수
schools = ["하안북중학교", "봉담중학교", "안천중학교", "가림중학교", "한국디지털미디어고등학교", "동탄국제고등학교"]
nega_words = ["않", "아니", "없", "싫"]
posi_words = ["응", "좋아", "맞아", "그래", "네"]

USER_DATA = 'users'
DATABASE = 'database'
os.makedirs(USER_DATA, exist_ok=True)
os.makedirs(DATABASE, exist_ok=True)

# 데이터베이스 로드
def load_database():
    global datas, hobbies, careers
    datas = {}
    hobbies = {}
    careers = {}
    
    key_word_path = os.path.join(DATABASE, 'key_words.json')
    hobbies_path = os.path.join(DATABASE, 'hobbies.json')
    careers_path = os.path.join(DATABASE, 'careers.json')
    
    if os.path.exists(key_word_path):
        with open(key_word_path, 'r', encoding='utf-8') as f:
            datas = json.load(f)
    if os.path.exists(hobbies_path):
        with open(hobbies_path, 'r', encoding='utf-8') as g:
            hobbies = json.load(g)
    if os.path.exists(careers_path):
        with open(careers_path, 'r', encoding='utf-8') as h:
            careers = json.load(h)

# 사용자 세션 관리 (웹 환경용)
user_sessions = {}

def get_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'last_topic': '',
            'chat_topic': '',
            'memory': '',
            'answer': ''
        }
    return user_sessions[user_id]

def check_user(user_id, user_pw):
    if id_check(user_id):
        return 'already'
    if any(char in user_id for char in ["#", "?", "!", "-", "_", "~", "*", "%", "&", "/", "@", "$"]):
        return 'special_banned'
    return 'allowed'

def check_consists(element, entire_list):
    for word in entire_list:
        if word in element:
            return True
    return False

def save_initial_data(user_id, user_pw, name, gender, age, school):
    initial_data = {
        'id': user_id,
        'password': user_pw,
        'name': name,
        'gender': gender,
        'age': age,
        'school': school
    }
    file_path = os.path.join(USER_DATA, f'{user_id}.json')
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(initial_data, f, ensure_ascii=False, indent=4)

def config_chat_data(user_id, content, type='initial'):
    file_path = os.path.join(USER_DATA, f'{user_id}_chat.json')
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
    else:
        chat_data = {'user_chat': [], 'bot_chat': []}
    
    if type == 'user_chat':
        chat_data['user_chat'].append(content)
    elif type == 'bot_chat':
        chat_data['bot_chat'].append(content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=4)
    
    return chat_data

def config_user_data(user_id, key, value):
    file_path = os.path.join(USER_DATA, f'{user_id}.json')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        if 'personal_data' not in user_data:
            user_data['personal_data'] = {}
        user_data['personal_data'][key] = value
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)

def analyze_followings(user_input, session):
    positive_detect = check_consists(user_input, posi_words)
    negative_detect = check_consists(user_input, nega_words)
    greeting_detect = check_consists(user_input, datas.get('greeting', []))
    
    if positive_detect:
        return 'positive'
    elif negative_detect:
        return 'negative'
    elif greeting_detect and session['chat_topic'] == 'greeting' and session['last_topic'] == 'greeting':
        return 're_greeting'
    return False

def id_check(user_id):
    file_path = os.path.join(USER_DATA, f'{user_id}.json')
    return os.path.exists(file_path)

def login_(input_id, input_pw):
    if not id_check(input_id):
        return False
    
    file_path = os.path.join(USER_DATA, f'{input_id}.json')
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if input_pw == data.get("password"):
        session = get_session(input_id)
        session['name'] = data.get('name')
        return True
    return False

def get_chat_history(user_id):
    file_path = os.path.join(USER_DATA, f'{user_id}_chat.json')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'user_chat': [], 'bot_chat': []}

def clear_chat_history(user_id):
    file_path = os.path.join(USER_DATA, f'{user_id}_chat.json')
    chat_data = {'user_chat': [], 'bot_chat': []}
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=4)
    
    session = get_session(user_id)
    session['last_topic'] = ''
    session['chat_topic'] = ''
    session['memory'] = ''

def detect_topic(user_input, session):
    session['chat_topic'] = ''
    
    # 유해성 검사
    try:
        responds = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "너는 사용자의 취미를 기반으로 진로를 찾아주는 데 필수적인 데이터를 제공하는 ai야."},
                {"role": "user", "content": f"다음 사용자의 질문에서 비속어, 욕설, 혐오표현, 차별적 표현, 범죄, 청소년에게 부적절한 콘텐츠가 있다면 yes 아니면 no라고 답해: {user_input}"}
            ],
            stream=False
        )
        response_text = responds.choices[0].message.content.strip()
        if 'yes' in response_text.lower():
            session['chat_topic'] = 'ban'
            return
    except Exception as e:
        print(f"API 오류: {e}")
        return
    
    # 키워드 매칭
    for key, value in datas.items():
        for data_word in value:
            if data_word in user_input:
                session['chat_topic'] = key
                session['memory'] = data_word
                break
    
    # 직업 키워드 매칭
    for key, value in careers.items():
        key_word_get = value.get("key_word", [])
        for key_word in key_word_get:
            if key_word in user_input:
                if session['chat_topic'] != 'career':
                    session['chat_topic'] = 'career'
                if key != session['memory']:
                    session['memory'] = key
    
    # AI로 취미/직업 추출
    if not session['chat_topic'] or not session['memory']:
        try:
            responds = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "너는 사용자의 취미를 기반으로 진로를 찾아주는 데 필수적인 데이터를 제공하는 ai야."},
                    {"role": "user", "content": f"다음 사용자의 메시지에서 (노래, 음악, 게임, 영화, 드라마, 웹툰, 웹소설, 운동)의 취미 종류가 있다면 취미 종류의 분류 이름을 하나만을 답하고, 아니면 \"No\"라고 답하세요: {user_input}"}
                ],
                stream=False
            )
            for hobby in hobbies.keys():
                if hobby in responds.choices[0].message.content:
                    session['chat_topic'] = 'hobby'
                    session['memory'] = hobby
                    return
            
            # 직업 정보 추출
            responds = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "너는 사용자의 취미를 기반으로 진로를 찾아주는 데 필수적인 데이터를 제공하는 ai야."},
                    {"role": "user", "content": f"다음 사용자의 메시지에서 직업 이름이 있다면, 이 직업의 이름과, 적성 3 어절, 추천 진학 학과 3개, 장점 문장 3개를 다음 포멧으로 작성하시오. 이름, 직업의 적성, 추천 진학 학과, 장점을 쉼표를 구분자로 각 항목별 내용을 작성하고, 슬래시 기호로 항목사이를 구별하시오. 예를 들어 '패션 디자이너/ 창의적 표현력, 트렌드 감각, 섬세한 손기술/패션디자인 학과, 의상디자인 학과, 섬유패션학과/사람들에게 ...., 트렌드를...., 자신만의....' 아니면 \"No\"라고 답하세요: {user_input}"}
                ],
                stream=False
            )
            response_text = responds.choices[0].message.content.strip()
            
            if response_text.lower() == "no" or "/" not in response_text:
                return
            
            parts = response_text.split('/')
            if len(parts) == 4:
                name = parts[0].strip()
                aptitude = [x.strip() for x in parts[1].split(',')]
                recommend = [x.strip() for x in parts[2].split(',')]
                benefit = [x.strip() for x in parts[3].split(',')]
                
                careers[name] = {
                    "key_word": [name],
                    "aptitude": aptitude,
                    "recommend": recommend,
                    "benefit": benefit
                }
                
                # careers.json 업데이트
                careers_path = os.path.join(DATABASE, 'careers.json')
                with open(careers_path, 'w', encoding='utf-8') as f:
                    json.dump(careers, f, ensure_ascii=False, indent=4)
                
                session['chat_topic'] = 'career'
                session['memory'] = name
        except Exception as e:
            print(f"파싱 중 오류: {e}")

def handle_greeting(user_input, user_name, session, re_greeting=None):
    respond = []
    if re_greeting == 're_greeting':
        respond.append('안녕하세요! 다시 인사하셨네요. 요즘 어떤 것에 관심이 있나요? 영화, 노래, 웹툰 같은 취미에 대해 이야기해 볼까요? 혹시 궁금한 직업이 있다면, 영상 편집자 같은 직업을 물어보세요.')
    else:
        respond.append(r.choice([f"안녕하세요, {user_name}님.", "안녕하세요!"]))
        respond.append(r.choice(["", "오늘은 무슨 이야기를 나눌까요?", "반갑습니다.", f"{user_name}님과 이야기 하게 되어 정말 좋아요."]))
        session['last_topic'] = 'greeting'
    return ' '.join(respond)

def handle_hobby(user_input, user_name, session, user_react=''):
    memory = session['memory']
    
    if user_react:
        if user_react == 'positive':
            respond = [f'좋아요!']
            config_user_data(user_name, 'hobby', memory)
            respond.append(hobbies.get(memory, {}).get('connect', '') + '\n')
            respond.append('그러면, 이 진로들에 대해 더 고민해볼까요?')
            session['last_topic'] = 'hobby_to_career'
            return ' '.join(respond)
        elif user_react == 'negative':
            respond = ['다른 관심사가 있나요? 진로가 고민이 되거나 관심 있는 직업이 있다면 같이 이야기해봐요!']
            session['last_topic'] = ''
            return ' '.join(respond)
        elif user_react == 're_greeting':
            return '안녕하세요?'
        return ''
    else:
        respond = [
            r.choice([f"와, {user_name}님, {memory}에 관심이 있으세요?", f"{user_name}님, {memory}에 관심이 있으신가요?"]),
            f'{memory}에 관심이 있으시면, 나중에 {memory} 분야에 도전해보는 것도 좋을 것 같아요.'
        ]
        session['last_topic'] = 'hobby_detail'
        return ' '.join(respond)

def connect_to_career(memory):
    for key, value in hobbies.items():
        if memory == key:
            return value.get('career', [])
    return []

def handle_career(user_input, session, user_react=''):
    user_name = session.get('name', '사용자')
    memory = session['memory']
    last_topic = session['last_topic']
    
    respond = []
    questions = ["어떤", "무슨", "뭐", "무엇"]
    not_sure = ["모르겠어", "몰라", "아직", "확실하지 않", "고민"]
    
    if check_consists(user_input, questions) and not memory:
        if check_consists(user_input, not_sure):
            return "아직 진로에 대해 고민이 많으시군요! 영화, 음악, 노래, 웹툰 중에 어떤 것에 관심이 있으세요? 같이 이야기해볼까요?"
        else:
            return f"{user_name}님에게 맞는 진로를 찾고 계시는군요!"
    
    has_career = False
    
    if user_react == 'positive':
        if last_topic == 'hobby_to_career':
            has_career = True
            memory = connect_to_career(memory)
            session['memory'] = memory
            respond.append(f'좋습니다. {user_name}님이 관심 있는 분야에 대해서 추천하고 싶은 직업은')
            for i in memory:
                respond.append(f'\n- {i}')
            respond.append(f'입니다.')
            respond.append(f'어떤 직업에 대해 자세히 알고 싶나요? 예를 들어 \'{r.choice(memory)}를 직업으로 삼기 위해 추천하는 진학 학과\'같은 것을 물어보세요!')
            session['last_topic'] = 'career_suggest'
        elif last_topic == 'career_suggest':
            respond.append('네, 어떤 직업을 자세히 알고 싶나요?')
        else:
            respond.append('네, 이 직업에 대해 어떤 점이 궁금하신가요?')
        return ' '.join(respond)
    
    elif user_react == 'negative':
        if last_topic == 'hobby_to_career':
            respond.append('지금은 이야기하고 싶지 않나요? 다른 진로에 관심이 있다면 언제든지 물어보세요!')
            session['last_topic'] = ''
        else:
            respond.append(f'제가 추천드린 진로가 마음에 들지 않으신가요? 스토리텔링 전문가 같은 {user_name}님의 관심사나 다른 궁금한 직업을 물어보세요~!')
        return ' '.join(respond)
    
    # 직업 상세 정보
    if memory in careers:
        has_career = True
    
    if has_career:
        return more_detail(user_input, session)
    elif session['chat_topic']:
        return '진로에 대해 궁금한 점이 있나요? 게임 개발자 같은 직업을 물어봐주세요.'
    return ''

def more_detail(user_input, session):
    memory = session['memory']
    respond = []
    
    if '학과' in user_input:
        school = "\n· ".join(careers[memory].get("recommend", []))
        respond.append(f'{memory}를 위해 추천하는 학과는 {school}입니다. 이 직업의 장점이 궁금하시면 "장점이 뭐야?"라고 물어보세요!')
        session['last_topic'] = 'career_merit'
    elif '장점' in user_input:
        benefits = ", ".join(careers[memory].get("benefit", []))
        respond.append(f"{memory}에는 주로 다음과 같은 장점이 있습니다.\n\n{benefits}\n\n")
        respond.append('다른 궁금한 점이 있나요? 이 직업을 가지기 위한 적성 같은 것을 물어보세요.')
        session['last_topic'] = 'career_merit'
    elif '적성' in user_input:
        requires = ", ".join(careers[memory].get("aptitude", []))
        respond.append(f"{memory} 직업을 가지려면 {requires}가 특히 중요합니다.")
        respond.append('이 직업이나 다른 직업에 대해 궁금한 점이 있다면 편하게 물어보세요!')
        session['last_topic'] = 'career_merit'
    elif session['chat_topic'] == 'career':
        respond.append(f"{memory}에 관심이 있으시군요!")
        s = "\n· ".join(careers[memory].get("recommend", []))
        requires = ", ".join(careers[memory].get("aptitude", []))
        respond.append(f"{memory} 직업을 가지려면 {requires}가 특히 중요합니다.")
        respond.append(f"추천 진학 학과:\n\n·{s}\n\n")
        benefits = ", ".join(careers[memory].get("benefit", []))
        respond.append(f"주로 다음과 같은 장점이 있습니다.\n\n{benefits}\n\n")
        respond.append("좋은 진로를 찾기 바랍니다!")
        session['memory'] = ''
        session['last_topic'] = ''
    
    return " ".join(respond)

# 초기화
load_database()