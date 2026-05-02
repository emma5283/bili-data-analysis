import streamlit as st
import pandas as pd
import plotly.express as px
import jieba
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re

# 1. 网页基础配置
st.set_page_config(page_title="B站历史深度数据看板", layout="wide")

@st.cache_data
def load_data():
    # 读取数据
    df = pd.read_excel("videoinfo.xlsx")
    # 数据清洗
    df['播放数'] = pd.to_numeric(df['播放数'], errors='coerce')
    # 修正时长：将秒转为分，并处理可能的负数（归零）
    df['时长(分)'] = (df['时长(秒)'].apply(lambda x: max(0, x))) / 60
    return df

df = load_data()

# --- 侧边栏：多维度筛选 ---
st.sidebar.header("数据筛选控制")
min_view = st.sidebar.slider("最小播放量", 0, int(df['播放数'].max()), 0)
selected_ups = st.sidebar.multiselect("筛选特定UP主", options=df['up主'].unique())

filtered_df = df[df['播放数'] >= min_view]
if selected_ups:
    filtered_df = filtered_df[filtered_df['up主'].isin(selected_ups)]

st.title("📊 B站历史类视频多维度深度看板")

# --- 第一部分：时长描述性统计 ---
st.header("⏳ 1. 视频时长统计概览")
mean_dur = filtered_df['时长(分)'].mean()
median_dur = filtered_df['时长(分)'].median()
max_dur = filtered_df['时长(分)'].max()
min_dur = filtered_df['时长(分)'].min()

# 指标卡展示
c1, c2, c3, c4 = st.columns(4)
c1.metric("平均时长", f"{mean_dur:.2f} min")
c2.metric("时长中位数", f"{median_dur:.2f} min")
c3.metric("最长视频", f"{max_dur:.2f} min")
c4.metric("最短视频", f"{min_dur:.2f} min")

st.info(f"**文字叙述：** 本组视频数据展现出明显的时间跨度。平均时长为 **{mean_dur:.2f}分钟**，而中位数为 **{median_dur:.2f}分钟**。如果平均值远高于中位数，说明数据中存在少数‘超长视频’拉高了均值，大多数视频其实集中在较短的时间区间内。")

# --- 第二部分：核心重点分析 (大图呈现) ---
st.header("🎯 2. 核心分析：时长与互动深度的关联")
st.write("此图表是我们分析的重点，反映了视频长度如何影响观众的‘三连’行为。")

with st.container():
    fig_deep = px.scatter(
        filtered_df, 
        x="时长(分)", 
        y="播放数", 
        size="点赞数",           # 气泡大小代表点赞
        color="收藏",           # 颜色深浅代表收藏
        hover_name="标题",
        hover_data=["up主", "点赞数", "收藏", "投硬币"],
        trendline="lowess",      # 局部加权回归趋势线
        template="plotly_white",
        height=800               # 显著加大图表高度
    )
    
    # 优化交互设置
    fig_deep.update_layout(
        xaxis=dict(title="视频时长 (分钟)", showgrid=True),
        yaxis=dict(title="播放总量", showgrid=True),
        dragmode='zoom' # 支持鼠标框选放大
    )
    
    # 渲染图表，并开启滚轮缩放
    st.plotly_chart(fig_deep, use_container_width=True, config={'scrollZoom': True})

# --- 第三部分：内容词云分析 ---
st.header("☁️ 3. 视频内容关键词云")
# 合并文本
text = " ".join(filtered_df['标题'].astype(str)) + " " + " ".join(filtered_df['简介'].dropna().astype(str))
text = "".join(re.findall(r'[\u4e00-\u9fa5]+', text))
words = [w for w in jieba.lcut(text) if len(w) > 1]
word_space = " ".join(words)

if word_space:
    # 注意：Windows 路径通常为 C:/Windows/Fonts/simhei.ttf
    wc = WordCloud(font_path="C:/Windows/Fonts/simhei.ttf", width=1200, height=500, background_color="white").generate(word_space)
    fig_wc, ax = plt.subplots(figsize=(10, 4))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis("off")
    st.pyplot(fig_wc)

# --- 第四部分：UP主分析 ---
st.header("👤 4. UP主影响力象限")
up_stats = filtered_df.groupby('up主').agg({'播放数': 'sum', '点赞数': 'sum', '标题': 'count'}).reset_index()
up_stats['点赞率'] = (up_stats['点赞数'] / up_stats['播放数'] * 100).round(2)

fig_up = px.scatter(up_stats, x="标题", y="播放数", text="up主", size="点赞率", color="点赞率",
                  labels={'标题': '投稿数量', '播放数': '总播放量'},
                  title="UP主发稿量 vs 播放量 (气泡大小/颜色代表点赞率)")
st.plotly_chart(fig_up, use_container_width=True)
