import streamlit as st
import pandas as pd
import numpy as np
import requests
from PIL import Image
from io import BytesIO
import altair as alt
import random

google_sheet_url = "https://docs.google.com/spreadsheets/d/1fDa292afd2TWIZtvNZl3R2tk2XMq1RGaC4o_pRCOUJE/edit?usp=sharing"

str_family_name_list = ["쭈니", "이뿐이", "누기", "랑이"]


# 보드게임 이름을 key로 필요한 데이터 저장
initial_boardgame_dic = {}
if "boardgame_dic" not in st.session_state:
    st.session_state.boardgame_dic = initial_boardgame_dic   
# 'play_count' 값을 기준으로 내림차순으로 key 정렬
initial_boardgame_play_count_sorted_keys = []
if "boardgame_play_count_sorted_keys" not in st.session_state:
    st.session_state.boardgame_play_count_sorted_keys = initial_boardgame_play_count_sorted_keys

#---------------------------------------------------------------------------
def load_public_google_sheet(url):
    try:
        # 스프레드시트 URL을 CSV 내보내기 URL로 변환
        if 'spreadsheets/d/' in url:
            # URL에서 스프레드시트 ID 추출
            sheet_id = url.split('spreadsheets/d/')[1].split('/')[0]
            csv_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv'
            
            # CSV 데이터를 DataFrame으로 읽기
            df = pd.read_csv(csv_url)
            return df
        else:
            st.error('올바른 Google 스프레드시트 URL이 아닙니다.')
            return None
            
    except Exception as e:
        st.error(f'데이터를 불러오는 중 오류가 발생했습니다: {str(e)}')
        return None

#---------------------------------------------------------------------------
def winner_score_count(list_scores):
    list_winner = [0] * len(str_family_name_list)
    list_nogame_count = [0] * len(str_family_name_list)
   
    # 최고 점수와 그에 해당하는 열 이름을 저장할 변수 초기화
    max_score = -1
   
    # scores 순회
    for index in range(0, len(list_scores)):
        # 숫자인지 체크
        if str(list_scores[index]).isdigit():
            # 숫자로 변환
            list_scores[index] = int(list_scores[index])
            # 최고 점수 찾기
            if list_scores[index] > max_score:
                max_score = list_scores[index]
        else:
            list_scores[index] = 0
            list_nogame_count[index] = 1

    # 같은 점수가 있는지 확인하고 같은 점수면 모두 winner가 된다
    for index in range(0, len(list_scores)):
        if (list_scores[index] == max_score):
            list_winner[index] = 1

    return list_scores, list_winner, list_nogame_count  

#---------------------------------------------------------------------------
# 보드게임 별 스코어를 받아, nogame을 숫자 0으로 변환하고, 등수별 승률값을 넣는다
def calculate_odds_scores(list_scores):
    odds_value = [100.0, 66.6, 33.3, 0.0]
    list_odds_scores = [0] * len(str_family_name_list)
    NO_GAME_VALUE = -1000
   
    # scores 순회
    for index in range(0, len(list_scores)):
        # 숫자인지 체크
        if str(list_scores[index]).isdigit():
            # 숫자로 변환
            list_scores[index] = int(list_scores[index])
        else:
            list_scores[index] = NO_GAME_VALUE
            
    # score을 오름차순했을때의 인덱스 리턴     
    # score[10, 30, 20, 50]이면, list_top_scores_index[3, 1, 2, 0]   
    list_top_scores_index = [i for _, i in sorted([(x, i) for i, x in enumerate(list_scores)], reverse=True)]
    
    # 높은 점수 순으로 승률 값을 부여한다 : 같은 점수면 같은 승률 부여
    # 점수가 [13, 10, 10, 8]이면, 등수[1, 2, 2, 4], 승률[100%, 66%, 66%, 0%]
    # 직전 점수(현재 1등)를 가지고, 다음 유저가 직전 점수와 같으면 같은 승률을 부여하기위한 변수
    index = 0
    rank_count = 0
    previous_score = list_scores[list_top_scores_index[index]] 
    # 1등 점수의 승률 부여
    list_odds_scores[list_top_scores_index[index]] = odds_value[rank_count]
    for index in range(1, len(list_top_scores_index)):
        # 게임에 참가 안 했으면 무조건 승률 0 부여해야 한다
        # !!!(주의) 아래 조건문이 없으면, score[10, 30, NO_GAME_VALUE, NO_GAME_VALUE]면, 승률[66%, 100%, 33%, 33%] 되는 문제 발생
        if (list_scores[list_top_scores_index[index]] == NO_GAME_VALUE):
            list_odds_scores[list_top_scores_index[index]] = 0
        else:
            # 이전 등수와 같으면 같은 승률, 다르면 다른 승률 부여
            if (list_scores[list_top_scores_index[index]] != previous_score): 
                rank_count = index
    
            list_odds_scores[list_top_scores_index[index]] = odds_value[rank_count]
            previous_score = list_scores[list_top_scores_index[index]] 

    return list_odds_scores    

#---------------------------------------------------------------------------
def parse_csvfile():
    # 구글 시트 데이터 로드
    df = load_public_google_sheet(google_sheet_url)
    
    # 보드게임 기본 정보 취득
    boardgame_dic = parse_boardgame_dic(df)
    
    return boardgame_dic     

#---------------------------------------------------------------------------
# 보드게임 이름을 key로 필요한 데이터를 저장한다
# boardgame_dic : 각 보드게임 플레이 횟수(play_count), 플레이 안 한 횟수(nogame_count), 이긴 횟수(winner_count[]), 최고점수(top_score[]), 평균점수(avg_score[]), 최근 플레이날짜(new_date)
# 평균점수(avg_score) : 여기서는 각 유저의 모든 점수를 더한다(나중에 평균 점수 계산이 필요할때, 플레이 횟수("play_count"-"nogame_count")로 나눠서 평균점수를 계산한다)
def parse_boardgame_dic(df):
    boardgame_dic = {}

    if df is not None:
        #index = 0
        for index in range(len(df)):
            # iloc: 정수 위치 기반 (0, 1, 2, ...)
            boardgame_name = df.iloc[index]['boardgame_name']
            # 보드게임 이름으로 같은 key가 있으면 데이터만 갱신한다
            if boardgame_name in boardgame_dic.keys():
                # loc: 레이블/조건 기반 (인덱스 이름, 열 이름)
                scores = df.loc[index, ["score_1", "score_2", "score_3", "score_4"]].tolist()
                list_scores, list_winner, list_nogame_count = winner_score_count(scores)
                list_odds_scores = calculate_odds_scores(scores)
                # 플레이 횟수 갱신
                boardgame_dic[boardgame_name]['play_count'] += 1
                for index in range(0, len(str_family_name_list)):
                    # 이긴 횟수 갱신
                    boardgame_dic[boardgame_name]['winner_count'][index] += list_winner[index]
                    # 플레이 안 한 횟수
                    boardgame_dic[boardgame_name]['nogame_count'][index] += list_nogame_count[index]
                    # 최고점수 갱신
                    boardgame_dic[boardgame_name]["top_score"][index] = max(boardgame_dic[boardgame_name]["top_score"][index], list_scores[index])  
                    # 평균점수 갱신 : 우선 모든 점수를 더하고 나중에 플레이 횟수("play_count"-"nogame_count")로 나눈다
                    boardgame_dic[boardgame_name]["avg_score"][index] += list_scores[index]  
                    # 승률점수 갱신
                    boardgame_dic[boardgame_name]["odds_score"][index] += list_odds_scores[index]
                
                # 최근 플레이날짜 갱신 (날짜 형식이 정확히 YY/MM/DD인 경우만 가능)
                boardgame_dic[boardgame_name]["new_date"] = max(boardgame_dic[boardgame_name]["new_date"], df.loc[index, 'play_date'])  
            # 보드게임 이름으로 key생성하고 초기 데이터 생성한다
            else:
                scores = df.loc[index, ["score_1", "score_2", "score_3", "score_4"]].tolist()
                list_scores, list_winner, list_nogame_count = winner_score_count(scores)
                list_odds_scores = calculate_odds_scores(scores)
                #new_date = df.loc[index, 'play_date']
                new_date = df.iloc[index]['play_date']
                icon_url = df.iloc[index]['icon_url']
                # !!!(주의) "top_score", "avg_score"는 list_scores.copy()를 이용한 값을 복사(깊은 복사) 한다 : {"top_score":list_scores}과 같이 할당(얕은 복사)을 하면 데이터가 공유되는 문제 발생
                boardgame_dic[boardgame_name] = {"play_count":1, "nogame_count":list_nogame_count, "winner_count":list_winner, "top_score":list_scores.copy(), "avg_score":list_scores.copy(), "odds_score":list_odds_scores.copy(), "new_date":new_date, "icon_url":icon_url}

        return boardgame_dic     

#---------------------------------------------------------------------------
def load_and_resize_image(url, size=(150, 150), quality='high'):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        
        # 리사이즈 품질 설정
        if quality == 'high':
            resample = Image.Resampling.LANCZOS
        elif quality == 'medium':
            resample = Image.Resampling.BILINEAR
        else:
            resample = Image.Resampling.NEAREST
            
        # 이미지 리사이즈
        resized_img = img.resize(size, resample)
        return resized_img
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None

#---------------------------------------------------------------------------
# 각 유저별 총 우승 횟수
def calculate_total_winner_count(boardgame_dict):
    total_winner_count = [0] * len(str_family_name_list)
    for value in boardgame_dict.values():
        total_winner_count = [x + y for x, y in zip(total_winner_count, value["winner_count"])]
    #print(total_winner_count)
    return total_winner_count    

#---------------------------------------------------------------------------
# 최다 1등
def calculate_total_top_winner(boardgame_dict):

    list_total_winner_count = calculate_total_winner_count(boardgame_dict)
    
    # 가장 높은 우승 횟수 찾기
    winner_count = 0
    for count in list_total_winner_count:
        if (winner_count < count):
            winner_count = count
    
    # 같은 우승 횟수 유저 찾기
    list_winner_user_index = []
    for index in range(0, len(list_total_winner_count)):
        if (winner_count == list_total_winner_count[index]):
            list_winner_user_index.append(index)
            
    # 이긴 유저 이름 리턴
    str_winner_users = ""
    for index in range(0, len(list_winner_user_index)):
        str_winner_users += str_family_name_list[list_winner_user_index[index]]
        if (index < len(list_winner_user_index) - 1):
            str_winner_users += " "

    return str_winner_users, winner_count, list_total_winner_count

#---------------------------------------------------------------------------
# 최다 플레이 게임 : 동일 등수가 있으면 최근에 플레이한 게임 선정
def calculate_total_top_play_game(boardgame_dict):
    top_play_boardgame_name = ""
    top_play_count = 0
    top_play_date = ""
    for key, value in boardgame_dict.items():
        if (top_play_count < value["play_count"]):
            top_play_boardgame_name = key
            top_play_count = value["play_count"]
            top_play_date = value["new_date"]

    # 같은 등수일때는 최근 플레이 게임 선정
    for key, value in boardgame_dict.items():
        if (top_play_count == value["play_count"]):
            if (top_play_date < value["new_date"]):
                top_play_boardgame_name = key
                top_play_date = value["new_date"]

    return top_play_boardgame_name, top_play_count
#---------------------------------------------------------------------------
# 최다 1등 승률
# 각 게임 등수별 승률 : [100%, 66.6%, 33.3%, 0%]
# 최종 승률 계산 : 각 게임 등수별 승률의 합 / 게임 수
#  ㄴ 예) 1등, 2등 한 경우 승률 : (100 + 66.6)/2 = 83.3% 
def calculate_total_top_odds(boardgame_dict):
    total_play_count = 0
    list_total_nogame_count = [0] * len(str_family_name_list)
    list_total_odds_scores = [0] * len(str_family_name_list)
    for value in boardgame_dict.values():
        # 총 play_count
        total_play_count += value["play_count"]
        # 총 nogame_count
        list_total_nogame_count = [x + y for x, y in zip(list_total_nogame_count, value["nogame_count"])]
        # 총 승률
        list_total_odds_scores = [x + y for x, y in zip(list_total_odds_scores, value["odds_score"])]
        
    # 실제 총 플레이 횟수
    list_total_play_count = [total_play_count - value for value in list_total_nogame_count]
    # 최종 승률
    list_total_odds_scores = [list_total_odds_scores[i] / list_total_play_count[i] for i in range(len(list_total_odds_scores))]

    return list_total_odds_scores
    
#---------------------------------------------------------------------------
#st.title('달랑두리의 보드게임 이야기')
st.markdown(f"<h3 style='color:white;'>달랑두리의 보드게임 이야기</h3>", unsafe_allow_html=True)
# 여백
st.markdown("<h3></h3>", unsafe_allow_html=True)

#---------------------------------------------------------------------------
# 종합
container = st.container(border=True)

st.session_state.boardgame_dic = parse_csvfile()         
# 'play_count' 값을 기준으로 내림차순으로 key 정렬
st.session_state.boardgame_play_count_sorted_keys = sorted(st.session_state.boardgame_dic.keys(), key=lambda x: st.session_state.boardgame_dic[x]["play_count"], reverse=True)
# 최대 플레이 게임
top_play_boardgame_name, top_play_count = calculate_total_top_play_game(st.session_state.boardgame_dic)
# 최다 우승자
str_winner_users, winner_count, list_total_winner_count = calculate_total_top_winner(st.session_state.boardgame_dic)
# 1등 승률
list_top_odds = calculate_total_top_odds(st.session_state.boardgame_dic)

# 제목
#container.subheader("종합")
# 구분선 추가
#container.markdown("<hr style='border: 2px solid rgba(0, 0, 255, 0.3); margin-top: 2px; margin-bottom: 50px;'>", unsafe_allow_html=True)

# 인기 게임
container.markdown(f"<h6 style='color:gray;'>인기 게임</h6>", unsafe_allow_html=True)
# 구분선 추가
container.markdown("<hr style='border: 0.5px solid rgba(210, 210, 210, 0.5); margin-top: 0px; margin-bottom: 0px;'>", unsafe_allow_html=True)
# 보드게임 이름
container.markdown(f"<h2 style='color:rgba(80, 80, 255, 0.8); font-weight:bold;'>{top_play_boardgame_name}</h2>", unsafe_allow_html=True)
# URL로 직접 이미지 표시
icon_url = st.session_state.boardgame_dic[top_play_boardgame_name]["icon_url"]
resized_img = load_and_resize_image(icon_url)
container.image(resized_img)
# 횟수
container.markdown(f"<h4 style='color:gray;'>{top_play_count} 회</h4>", unsafe_allow_html=True)

# 여백
container.markdown("<h4></h4>", unsafe_allow_html=True)

# 최다 1등(챔피언)
container.markdown(f"<h6 style='color:gray;'>챔피언</h6>", unsafe_allow_html=True)
# 구분선 추가
container.markdown("<hr style='border: 0.5px solid rgba(210, 210, 210, 0.5); margin-top: 0px; margin-bottom: 0px;'>", unsafe_allow_html=True)
# 챔피언 이름
container.markdown(f"<h2 style='color:rgba(80, 80, 255, 0.8); font-weight:bold;'>{str_winner_users}</h2>", unsafe_allow_html=True)
# 횟수
container.markdown(f"<h4 style='color:gray; border: 2px; margin-top: 5px; margin-bottom: 0px;'>{winner_count} 회</h4>", unsafe_allow_html=True)

# 여백
container.markdown("<h3></h3>", unsafe_allow_html=True)

# 우승 횟수 막대 그래프
total_winner_count = calculate_total_winner_count(st.session_state.boardgame_dic)
# 데이터 생성
data = pd.DataFrame({' ':str_family_name_list, '우승 횟수':total_winner_count})
# Altair 차트 설정 (x축에 따른 그룹화 및 y축 정수 표시)
# axis=alt.Axis(format='d') : 정수로 표시하도록 설정
# x 값에 따라 색상 지정
#chart = alt.Chart(data).mark_bar().encode(x=alt.X('우승 횟수', axis=alt.Axis(format='d')), y=alt.Y(' ', sort=None), color=' :N'  )
chart = alt.Chart(data).mark_bar().encode(x=alt.X(' ', sort=None), y=alt.Y('우승 횟수', axis=alt.Axis(format='d')), color=' :N'  )
# 막대 차트 : st.altair_chart()
container.altair_chart(chart, use_container_width=True)
# 막대 차트 : st.bar_chart()
#data['name'] = pd.Categorical(data['name'], categories=data['name'].tolist(), ordered=True)
#st.bar_chart(data, x="name", y="우승 횟수", horizontal=False)

# 우승 횟수, 승률
# 탭 설정
tab1, tab2 = container.tabs(["우승", "승률"])
with tab1:
    # 값을 오름차순했을때의 인덱스 리턴
    list_sorted_value_index = [i for _, i in sorted([(x, i) for i, x in enumerate(list_total_winner_count)], reverse=True)]
    list_sorted_family_name = []
    list_sorted_value = []
    for index, value in enumerate(list_sorted_value_index):
        list_sorted_family_name.append(str_family_name_list[value])
        list_sorted_value.append(list_total_winner_count[value])
        
    list_value_data = {"이름":list_sorted_family_name,"횟수":list_sorted_value}
    df = pd.DataFrame(list_value_data)
    df["이름"] = df["이름"].astype(str)  # 이름 컬럼을 문자열로 변환
    df["횟수"] = df["횟수"].astype(int)  # 횟수 컬럼을 정수로 변환 
    # "T" 행렬 변환, "rename"는 행의 컬럼을 0이 아닌 1에서 오름차순 표시되도록 변환
    st.dataframe(df.T.rename(columns=lambda x: x + 1))    
    
with tab2:
    # 값을 오름차순했을때의 인덱스 리턴
    list_sorted_value_index = [i for _, i in sorted([(x, i) for i, x in enumerate(list_top_odds)], reverse=True)]
    list_sorted_family_name = []
    list_sorted_value = []
    for index, value in enumerate(list_sorted_value_index):
        list_sorted_family_name.append(str_family_name_list[value])
        list_sorted_value.append(f"{list_top_odds[value]:.1f}%")
        
    list_value_data = {"이름":list_sorted_family_name,"승률":list_sorted_value}
    df = pd.DataFrame(list_value_data)
    df["이름"] = df["이름"].astype(str)  # 이름 컬럼을 문자열로 변환
    df["승률"] = df["승률"].astype(str)  # 횟수 컬럼을 정수로 변환 
    # "T" 행렬 변환, "rename"는 행의 컬럼을 0이 아닌 1에서 오름차순 표시되도록 변환
    st.dataframe(df.T.rename(columns=lambda x: x + 1))    

#---------------------------------------------------------------------------
# 여백
st.markdown("<h3></h3>", unsafe_allow_html=True)

#---------------------------------------------------------------------------
# 보드게임
# 게임 횟수, 최근 플레이 date, 각 유저 우승 현황, 각 유저 평균 점수, 각 유저 최고 점수
for index in range(len(st.session_state.boardgame_dic)):
    boardgame_name = st.session_state.boardgame_play_count_sorted_keys[index]

    container = st.container(border=True)
    container.markdown(f"<h4 style='font-weight:bold;'>{index+1}. {boardgame_name}</h4>", unsafe_allow_html=True)
    # 구분선 추가
    container.markdown("<hr style='border: 2px solid rgba(255, 100, 100, 0.3); margin-top: 2px; margin-bottom: 40px;'>", unsafe_allow_html=True)
    
    # URL로 직접 이미지 표시
    icon_url = st.session_state.boardgame_dic[boardgame_name]["icon_url"]
    resized_img = load_and_resize_image(icon_url)
    container.image(resized_img)
    # 횟수
    play_count = st.session_state.boardgame_dic[boardgame_name]['play_count']
    container.markdown(f"<h5>{play_count} 회</h5>", unsafe_allow_html=True)
    
    # 탭 설정
    tab1, tab2, tab3, tab4 = container.tabs(["우승", "승률", "최고 점수", "평균 점수"])
    # 우승 횟수
    with tab1:
        list_value = st.session_state.boardgame_dic[boardgame_name]['winner_count']
        # 값을 오름차순했을때의 인덱스 리턴
        list_sorted_value_index = [i for _, i in sorted([(x, i) for i, x in enumerate(list_value)], reverse=True)]
        list_sorted_family_name = []
        list_sorted_value = []
        for index, value in enumerate(list_sorted_value_index):
            list_sorted_family_name.append(str_family_name_list[value])
            list_sorted_value.append(list_value[value])
            
        list_value_data = {"이름":list_sorted_family_name,"횟수":list_sorted_value}
        df = pd.DataFrame(list_value_data)
        df["이름"] = df["이름"].astype(str)  # 이름 컬럼을 문자열로 변환
        df["횟수"] = df["횟수"].astype(int)  # 횟수 컬럼을 정수로 변환 
        # "T" 행렬 변환, "rename"는 행의 컬럼을 0이 아닌 1에서 오름차순 표시되도록 변환
        st.dataframe(df.T.rename(columns=lambda x: x + 1))
        
    # 승률
    with tab2:
        play_count = st.session_state.boardgame_dic[boardgame_name]['play_count']
        list_nogame_count = st.session_state.boardgame_dic[boardgame_name]['nogame_count']
        list_play_count = [play_count - value for value in list_nogame_count]
        list_value = st.session_state.boardgame_dic[boardgame_name]['odds_score']
        list_odds_value = [list_value[i] / list_play_count[i] for i in range(len(list_value))]
        # 값을 오름차순했을때의 인덱스 리턴
        list_sorted_value_index = [i for _, i in sorted([(x, i) for i, x in enumerate(list_odds_value)], reverse=True)]
        list_sorted_family_name = []
        list_sorted_value = []
        for index, value in enumerate(list_sorted_value_index):
            list_sorted_family_name.append(str_family_name_list[value])
            list_sorted_value.append(f"{list_odds_value[value]:.1f}%")
            
        list_value_data = {"이름":list_sorted_family_name,"점수":list_sorted_value}
        df = pd.DataFrame(list_value_data)
        df["이름"] = df["이름"].astype(str)  # 이름 컬럼을 문자열로 변환
        df["점수"] = df["점수"].astype(str)  # 횟수 컬럼을 정수로 변환        
        # "T" 행렬 변환, "rename"는 행의 컬럼을 0이 아닌 1에서 오름차순 표시되도록 변환
        st.dataframe(df.T.rename(columns=lambda x: x + 1))
              
    # 최고 점수
    with tab3:
        list_value = st.session_state.boardgame_dic[boardgame_name]['top_score']
        # 값을 오름차순했을때의 인덱스 리턴
        list_sorted_value_index = [i for _, i in sorted([(x, i) for i, x in enumerate(list_value)], reverse=True)]
        list_sorted_family_name = []
        list_sorted_value = []
        for index, value in enumerate(list_sorted_value_index):
            list_sorted_family_name.append(str_family_name_list[value])
            list_sorted_value.append(list_value[value])
            
        list_value_data = {"이름":list_sorted_family_name,"점수":list_sorted_value}
        df = pd.DataFrame(list_value_data)
        df["이름"] = df["이름"].astype(str)  # 이름 컬럼을 문자열로 변환
        df["점수"] = df["점수"].astype(int)  # 횟수 컬럼을 정수로 변환
        # "T" 행렬 변환, "rename"는 행의 컬럼을 0이 아닌 1에서 오름차순 표시되도록 변환
        st.dataframe(df.T.rename(columns=lambda x: x + 1))
    
    # 평균 점수
    with tab4:
        play_count = st.session_state.boardgame_dic[boardgame_name]['play_count']
        list_nogame_count = st.session_state.boardgame_dic[boardgame_name]['nogame_count']
        list_play_count = [play_count - value for value in list_nogame_count]
        list_value = st.session_state.boardgame_dic[boardgame_name]['avg_score']
        list_avg_value = [list_value[i] / list_play_count[i] for i in range(len(list_value))]
        # 값을 오름차순했을때의 인덱스 리턴
        list_sorted_value_index = [i for _, i in sorted([(x, i) for i, x in enumerate(list_avg_value)], reverse=True)]
        list_sorted_family_name = []
        list_sorted_value = []
        for index, value in enumerate(list_sorted_value_index):
            list_sorted_family_name.append(str_family_name_list[value])
            list_sorted_value.append(list_avg_value[value])
            
        list_value_data = {"이름":list_sorted_family_name,"점수":list_sorted_value}
        df = pd.DataFrame(list_value_data)
        df["이름"] = df["이름"].astype(str)  # 이름 컬럼을 문자열로 변환
        df["점수"] = df["점수"].astype(int)  # 횟수 컬럼을 정수로 변환        
        # "T" 행렬 변환, "rename"는 행의 컬럼을 0이 아닌 1에서 오름차순 표시되도록 변환
        st.dataframe(df.T.rename(columns=lambda x: x + 1))
      
#---------------------------------------------------------------------------
# 보드게임
#cols = st.columns(2)
#for index in range(len(st.session_state.boardgame_dic)):
#    with cols[index % 2]:
#        boardgame_name = st.session_state.boardgame_play_count_sorted_keys[index]

#        container = st.container(border=True)
#        container.markdown(f"<h4 style='color:rgba(240, 240, 230, 1.0); font-weight:bold;'>{index+1}. {boardgame_name}</h4>", unsafe_allow_html=True)
        # 구분선 추가
#        container.markdown("<hr style='border: 2px solid rgba(255, 100, 100, 1.0); margin-top: 2px; margin-bottom: 40px;'>", unsafe_allow_html=True)

        # 이미지를 가운데 정렬하기 위한 무식한 방법
#        header = container.columns([1,0.3])
        # URL로 직접 이미지 표시
#        icon_url = st.session_state.boardgame_dic[boardgame_name]["icon_url"]
#        resized_img = load_and_resize_image(icon_url)
#        header[0].image(resized_img)
#        play_count = st.session_state.boardgame_dic[boardgame_name]['play_count']
#        header[1].markdown(f"<h4>{play_count} 회</h4>", unsafe_allow_html=True)
        #container.image(resized_img)        
