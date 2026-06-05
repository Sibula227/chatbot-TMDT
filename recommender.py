import mysql.connector
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import HTTPException

# --- HÀM LẤY DỮ LIỆU THẬT TỪ DATABASE MYSQL ---
def get_user_item_data_from_mysql():
    db_config = {
        'host': 'localhost',
        'user': 'user db',          # Thay bằng username của bạn
        'password': 'mk db',      # Thay bằng mật mã MySQL của bạn
        'database': 'ten db'    # Thay bằng tên database của bạn
    }
    try:
        conn = mysql.connector.connect(**db_config)
        query = "SELECT user_id, product_id, rating_value AS rating FROM ratings"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
        
    except mysql.connector.Error as err:
        print(f"Lỗi kết nối MySQL: {err}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(err)}")

# --- THUẬT TOÁN COLLABORATIVE FILTERING ---
def get_collaborative_recommendations(target_user_id: int, top_n: int):
    df = get_user_item_data_from_mysql()
    
    if df.empty or target_user_id not in df['user_id'].values:
        return []

    user_item_matrix = df.pivot_table(index='user_id', columns='product_id', values='rating').fillna(0)
    
    user_similarity = cosine_similarity(user_item_matrix)
    similarity_df = pd.DataFrame(user_similarity, index=user_item_matrix.index, columns=user_item_matrix.index)
    
    similar_users = similarity_df[target_user_id].sort_values(ascending=False).index[1:]
    target_user_rated_items = set(df[df['user_id'] == target_user_id]['product_id'])
    
    recommendations = {}
    for similar_user in similar_users:
        similar_user_items = df[(df['user_id'] == similar_user) & (df['rating'] >= 4)]
        for _, row in similar_user_items.iterrows():
            item = row['product_id']
            if item not in target_user_rated_items:
                if item not in recommendations:
                    recommendations[item] = row['rating'] * similarity_df[target_user_id][similar_user]
                    
    sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
    return [item[0] for item in sorted_recs[:top_n]]