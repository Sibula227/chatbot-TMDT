import pandas as pd
import pymysql
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
def get_interaction_data():
    # Kết nối cơ sở dữ liệu MySQL
    conn = pymysql.connect(
        host="localhost",
        user="root",               # Tên user MySQL 
        password="24032005",  # Mật khẩu MySQL của bạn
        database="ecommerce_db",   # Thay bằng tên database dự án
        port=3306,
        charset='utf8mb4'
    )
    
    query = """
            SELECT
                reviewer_name AS user_id,
                product_id,
                rating_stars AS rating
            FROM product_reviews
            WHERE rating_stars IS NOT NULL;
            """
    # Dùng read_sql_query để tránh warning của pandas ở các phiên bản mới
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def build_recommendation_engine():
    df = get_interaction_data()
    print("========== Interaction Data ==========")
    print(df.head(10))
    print("Số reviewer:", df["user_id"].nunique())
    print("Số sản phẩm:", df["product_id"].nunique())
    print("======================================")
    # Tạo ma trận User-Item
    user_item_matrix = df.pivot_table(
    index="user_id",
    columns="product_id",
    values="rating",
    aggfunc="mean",
    fill_value=0
    )
    print("User-Item Matrix:", user_item_matrix.shape)
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
def get_similar_products(product_id, top_n=5):
    _, item_similarity_df = build_recommendation_engine()

    print("Product:", product_id)

    if product_id not in item_similarity_df.columns:
        print("Không có product")
        return []

    similar_items = item_similarity_df[product_id].sort_values(ascending=False)

    print("Top Similar:")
    print(similar_items.head(10))

    return similar_items.index.tolist()[1:top_n+1]
def get_product_specs_data():
    """Lấy dữ liệu thông số kỹ thuật từ database"""
    conn = pymysql.connect(
        host="localhost",
        user="root",               
        password="24032005",  
        database="ecommerce_db",   
        port=3306,
        charset='utf8mb4'
    )
    
    # Lấy thông số kỹ thuật của tất cả sản phẩm
    query = """
            SELECT product_id, spec_key, spec_value 
            FROM product_specs 
            WHERE spec_value IS NOT NULL AND spec_value != '';
            """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def build_content_based_engine():
    df = get_product_specs_data()
    print("========== Product Specs Data ==========")
    print(f"Tổng số dòng thông số: {len(df)}")
    
    # Gom tất cả spec_value của 1 product_id thành một chuỗi text duy nhất
    # Ví dụ: Product 1 -> "Adreno 840 Snapdragon 8 Gen 2 8GB 256GB 120Hz"
    # Bước này tạo ra "Hồ sơ" (Profile) cho từng sản phẩm
    product_profiles = df.groupby('product_id')['spec_value'].apply(lambda x: ' '.join(x.astype(str))).reset_index()
    product_profiles.set_index('product_id', inplace=True)
    
    print(f"Số lượng sản phẩm có specs: {len(product_profiles)}")
    print("========================================")

    # Sử dụng TF-IDF để chuyển text thành ma trận vector
    # Loại bỏ các từ quá phổ biến (nếu có), nhưng với specs thì cứ lấy mặc định
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(product_profiles['spec_value'])
    
    # Tính toán Cosine Similarity trên ma trận TF-IDF
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    # Trả về ma trận tương đồng kèm index là product_id để dễ truy xuất
    cbf_similarity_df = pd.DataFrame(cosine_sim, index=product_profiles.index, columns=product_profiles.index)
    
    return cbf_similarity_df

def get_content_based_similar_products(product_id, top_n=5):
    """Lấy danh sách gợi ý bằng Content-Based Filtering"""
    cbf_similarity_df = build_content_based_engine()
    
    print(f"Content-Based Request cho Product ID: {product_id}")
    
    # Nếu sản phẩm không có thông số kỹ thuật trong hệ thống
    if product_id not in cbf_similarity_df.columns:
        print(f"Không có dữ liệu specs cho product: {product_id}")
        return []
        
    # Lấy độ tương đồng của sản phẩm này với các sản phẩm khác, sắp xếp giảm dần
    similar_items = cbf_similarity_df[product_id].sort_values(ascending=False)
    
    # Bỏ qua index đầu tiên (chính là sản phẩm đó, độ tương đồng = 1.0)
    # Lấy top_n sản phẩm tiếp theo
    recommendations = similar_items.iloc[1:top_n+1].index.tolist()
    
    print(f"Top {top_n} CBF Recommendations: {recommendations}")
    return recommendations