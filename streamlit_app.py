import streamlit as st
import pandas as pd
import altair as alt
import locale
import math

# 한국어 로케일 설정
locale.setlocale(locale.LC_TIME, 'ko_KR.UTF-8')

# Streamlit Debug Mode 활성화
st.set_page_config(page_title='전설의 패치 리뷰 분석 대시보드', layout='wide')

debug = True

# 파일 참조
st.title('전설의 패치 리뷰 분석 대시보드')

# 이미 존재하는 파일 참조
file_path = '전설의패치_reviews.xlsx'

# 파일 읽기
if file_path.endswith('csv'):
    df = pd.read_csv(file_path)
elif file_path.endswith('xlsx'):
    df = pd.read_excel(file_path)

# 날짜 컬럼을 datetime 형식으로 변환
df['리뷰 작성시간'] = pd.to_datetime(df['리뷰 작성시간'])

# 추가 정보 값에 따른 카테고리 정의
category_mapping = {
    1: '피부 자극 및 부작용',
    2: '접착력 문제',
    3: '효과 부족',
    4: '가격 대비 성능 불만',
    5: '파스 냄새 및 사용감',
    6: '기대 이하의 성능',
    7: '기타'
}
df['category'] = df['추가정보'].map(category_mapping)

# 각 카테고리별 부정 리뷰 개수 및 20일에 평균 대비 변화량 계산
cols = st.columns(4)
for i, category in enumerate(category_mapping.values()):
    col = cols[i % len(cols)]
    category_df = df[df['category'] == category]
    negative_count = len(category_df[category_df['sentiment'] == 1])
    avg_negative_count = negative_count / len(category_df['리뷰 작성시간'].unique()) if len(category_df['리뷰 작성시간'].unique()) > 0 else 0
    count_20 = len(category_df[(category_df['sentiment'] == 1) & (category_df['리뷰 작성시간'].dt.date == pd.to_datetime('2024-10-20').date())])
    delta = ((count_20 - avg_negative_count) / avg_negative_count * 100) if avg_negative_count > 0 else 0

    with col:
        st.metric(
            label=f'{category} 부정 리뷰 개수',
            value=f'{count_20}',
            delta=f'{delta:+.2f}%',
            delta_color='normal'
        )

# Streamlit에서 보기 간격 선택 버튼 추가
interval = st.radio('보기 간격 선택', ['1일 간격', '7일 간격', '1개월 간격'], horizontal=True)

# 선택된 간격에 따라 sentiment 값이 1인 데이터 집계
sentiment_1_df = df[df['sentiment'] == 1]
if interval == '1일 간격':
    all_dates = pd.date_range(start='2024-10-12', end='2024-10-21', freq='D')
    sentiment_1_count = sentiment_1_df.set_index('리뷰 작성시간').resample('D').size().reindex(all_dates, fill_value=0).reset_index(name='count')
    sentiment_1_count.rename(columns={'index': '리뷰 작성시간'}, inplace=True)
elif interval == '7일 간격':
    sentiment_1_count = sentiment_1_df.set_index('리뷰 작성시간').resample('W').size().reset_index(name='count')
elif interval == '1개월 간격':
    sentiment_1_count = sentiment_1_df.set_index('리뷰 작성시간').resample('M').size().reset_index(name='count')

# 데이터가 존재하는 범위 내에서만 그래프를 그리도록 수정
if not sentiment_1_count.empty:
    # Altair를 사용해 sentiment 값이 1인 리뷰 빈도수를 선 그래프로 표시 (주황색 선)
    sentiment_line_chart = alt.Chart(sentiment_1_count).mark_line(color='orange').encode(
        x=alt.X('리뷰 작성시간:T', title='날짜', axis=alt.Axis(format='%Y-%m-%d', labelAngle=-45)),
        y=alt.Y('count:Q', title='부정적인 댓글 개수')
    ).properties(
        title='날짜별 부정적인 댓글 개수'
    )

    st.altair_chart(sentiment_line_chart, use_container_width=True)
else:
    st.warning("선택한 간격에 해당하는 데이터가 없습니다.")

# 카테고리 선택란 추가
selected_categories = st.multiselect('카테고리 선택', options=list(category_mapping.values()), default=list(category_mapping.values()))
filtered_df = df[df['category'].isin(selected_categories)]

# 선택된 간격에 따라 카테고리별 데이터 집계
if interval == '1일 간격':
    all_dates = pd.date_range(start='2024-10-12', end='2024-10-21', freq='D')
    category_count = filtered_df.set_index('리뷰 작성시간').groupby([pd.Grouper(freq='D'), 'category']).size().unstack(fill_value=0).reindex(all_dates, fill_value=0).stack().reset_index(name='count')
    category_count.rename(columns={'level_0': '리뷰 작성시간'}, inplace=True)
elif interval == '7일 간격':
    category_count = filtered_df.set_index('리뷰 작성시간').groupby([pd.Grouper(freq='W'), 'category']).size().reset_index(name='count')
elif interval == '1개월 간격':
    category_count = filtered_df.set_index('리뷰 작성시간').groupby([pd.Grouper(freq='M'), 'category']).size().reset_index(name='count')

# 데이터가 존재하는 범위 내에서만 그래프를 그리도록 수정
if not category_count.empty:
    # Altair를 사용해 각 카테고리의 빈도수를 누적 막대 그래프로 표시
    category_bar_chart = alt.Chart(category_count).mark_bar().encode(
        x=alt.X('리뷰 작성시간:T', title='날짜', axis=alt.Axis(format='%Y-%m-%d', labelAngle=-45)),
        y=alt.Y('count:Q', title='리뷰 빈도수', stack='zero'),
        color='category:N'
    ).properties(
        title='날짜별 리뷰 카테고리 빈도수 (누적 막대 그래프)'
    )

    st.altair_chart(category_bar_chart, use_container_width=True)

    # Altair를 사용해 각 카테고리의 빈도수를 선 그래프로 표시
    category_line_chart = alt.Chart(category_count).mark_line().encode(
        x=alt.X('리뷰 작성시간:T', title='날짜', axis=alt.Axis(format='%Y-%m-%d', labelAngle=-45)),
        y=alt.Y('count:Q', title='리뷰 빈도수'),
        color='category:N'
    ).properties(
        title='날짜별 리뷰 카테고리 빈도수 (선 그래프)'
    )

    st.altair_chart(category_line_chart, use_container_width=True)
else:
    st.warning("선택한 간격에 해당하는 데이터가 없습니다.")

# '기타' 카테고리의 10월 21일 데이터 필터링
etc_category_21_df = df[(df['category'] == '기타') & (df['리뷰 작성시간'].dt.date == pd.to_datetime('2024-10-21').date())]

# '기타' 카테고리의 10월 21일 데이터 테이블 표시
if not etc_category_21_df.empty:
    st.write("기타 카테고리의 10월 21일 추가된 리뷰:")
    st.dataframe(etc_category_21_df[['작성 리뷰 평점', '리뷰 내용']])
else:
    st.info("10월 21일에 추가된 '기타' 카테고리 데이터가 없습니다.")

# '기타' 카테고리의 10월 20일 데이터 필터링
etc_category_20_df = df[(df['category'] == '기타') & (df['리뷰 작성시간'].dt.date == pd.to_datetime('2024-10-20').date())]

# '기타' 카테고리의 10월 20일 데이터 테이블 표시
if not etc_category_20_df.empty:
    st.write("기타 카테고리의 10월 20일 추가된 리뷰:")
    st.dataframe(etc_category_20_df[['작성 리뷰 평점', '리뷰 내용']])
else:
    st.info("10월 20일에 추가된 '기타' 카테고리 데이터가 없습니다.")
