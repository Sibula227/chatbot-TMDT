import pandas as pd
import pymysql
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def get_interaction_data():
    # Kết nối cơ sở dữ liệu MySQL
    conn = pymysql.connect(
        host="localhost",
        user="root",               # Tên user MySQL 
        password="your_password",  # Mật khẩu MySQL của bạn
        database="ten_db",   # Thay bằng tên database dự án
        port=3306,
        charset='utf8mb4'
    )
    
    query = "SELECT user_id, product_id, rating FROM ratings;"
    # Dùng read_sql_query để tránh warning của pandas ở các phiên bản mới
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def build_recommendation_engine():
    df = get_interaction_data()
    
    # Tạo ma trận User-Item
    user_item_matrix = df.pivot_table(index='user_id', columns='product_id', values='rating').fillna(0)
    
    # Tính toán độ tương đồng Cosine
    item_similarity = cosine_similarity(user_item_matrix.T)
    item_similarity_df = pd.DataFrame(item_similarity, index=user_item_matrix.columns, columns=user_item_matrix.columns)
    
    return user_item_matrix, item_similarity_df

def get_recommendations(user_id, top_n=5):
    user_item_matrix, item_similarity_df = build_recommendation_engine()
    
    # Xử lý Cold Start (Người dùng chưa từng có đánh giá nào)
    if user_id not in user_item_matrix.index:
        return [] 
        
    user_ratings = user_item_matrix.loc[user_id]
    
    # Tính toán và dự đoán điểm cho các sản phẩm
    similar_scores = item_similarity_df.dot(user_ratings) / np.array([np.abs(item_similarity_df).sum(axis=1)]).ravel()
    similar_scores = pd.Series(similar_scores, index=item_similarity_df.columns)
    
    # Loại bỏ những sản phẩm đã tương tác
    already_interacted = user_ratings[user_ratings > 0].index
    recommendations = similar_scores.drop(already_interacted).sort_values(ascending=False)
    
    # Trả về danh sách ID sản phẩm
    return recommendations.head(top_n).index.tolist()