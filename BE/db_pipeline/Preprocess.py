from konlpy.tag import Komoran
import pickle
import jpype
import re

class Preprocess:
    def __init__(self, word2index_dic='', userdic=None):
        # 단어 인덱스 사전 불러오기
        if(word2index_dic != ''):
            f = open(word2index_dic, "rb")
            self.word_index = pickle.load(f)
            # a = 0
            # for i in self.word_index:
            #     print(i, '"',self.word_index[i])
            #     a = a + 1
            #     if a == 1000:
            #         break
            # print(type(self.word_index))
            f.close()
        else:
            self.word_index = None

        # 형태소 분석기 초기화
        self.komoran = Komoran(userdic=userdic)

        # 제외할 품사
        # 참조 : https://docs.komoran.kr/firststep/postypes.html
        # 관계언 제거, 기호 제거
        # 어미 제거
        # 접미사 제거
        self.exclusion_tags = [
            'JKS', 'JKC', 'JKG', 'JKO', 'JKB', 'JKV', 'JKQ',
            'JX', 'JC',
            'SF', 'SP', 'SS', 'SE', 'SO',
            'EP', 'EF', 'EC', 'ETN', 'ETM',
            'XSN', 'XSV', 'XSA'
        ]
    def remove_emojis(self, text):
        # 텍스트가 None이거나 비어있는 경우 처리
        if not text:
            return ""
        
        # UTF-8 인코딩 오류 방지를 위한 안전한 처리
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')
            
            # 이모지만 정확하게 타겟팅하여 제거 (한글, 영어, 숫자, 기본 기호는 보존)
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # 감정 이모티콘
                "\U0001F300-\U0001F5FF"  # 기호 및 그림문자
                "\U0001F680-\U0001F6FF"  # 교통 및 지도 기호
                "\U0001F700-\U0001F77F"  # 연금술 기호
                "\U0001F780-\U0001F7FF"  # 기하학적 모양 확장
                "\U0001F800-\U0001F8FF"  # 보조 화살표-C
                "\U0001F900-\U0001F9FF"  # 보조 기호 및 그림문자
                "\U0001FA00-\U0001FA6F"  # 체스 기호
                "\U0001FA70-\U0001FAFF"  # 기호 및 그림문자 확장-A
                "\U0001F1E0-\U0001F1FF"  # 국기
                "\u200d"                 # 제로 폭 결합자
                "\ufe0f"                 # 변형 선택자
                "]+", 
                flags=re.UNICODE
            )
            
            # 이모지 제거
            cleaned_text = emoji_pattern.sub('', text)
            
            # 불필요한 공백 제거
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            
            # 한글, 영어, 숫자, 기본 기호는 유지
            cleaned_text = re.sub(r'[^\w\s가-힣.,!?<>:;\'\"()\[\]{}\-]', '', cleaned_text)
            
            return cleaned_text.strip()
            
        except Exception as e:
            print(f"[에러] 이모지 제거 중 오류: {e}")
            # 에러 발생 시 기본적인 정리만 수행
            return re.sub(r'[^\w\s가-힣]', ' ', str(text))
    
    # 형태소 분석기 POS 태거
    def pos(self, sentence):
        # print(f"[디버그] 형태소 분석 시작: {sentence}")
        sentence = self.remove_emojis(sentence)
        # print(f"[디버그] 형태소 분석 전 문장: {sentence}")
        jpype.attachThreadToJVM()
        return self.komoran.pos(sentence)
    
    # 불용어 제거 후, 필요한 품사 정보만 가져오기
    def get_keywords(self, pos, without_tag=False):
        f = lambda x: x in self.exclusion_tags
        word_list = []
        for p in pos:
            if f(p[1]) is False:
                word_list.append(p if without_tag is False else p[0])

        return word_list

    # 키워드를 단어 인덱스 시퀀스로 변환
    def get_wordidx_sequence(self, keywords):
        if self.word_index is None:
            return []

        w2i = []
        for word in keywords:
            try:
                w2i.append(self.word_index[word])
            except KeyError:
                # 해당 단어가 사전에 없는 경우, OOV 처리
                w2i.append(self.word_index['OOV'])
        return w2i

