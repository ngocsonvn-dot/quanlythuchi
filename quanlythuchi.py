import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from supabase import create_client, Client

# --- CẤU HÌNH KẾT NỐI ĐÁM MÂY SUPABASE ---
SUPABASE_URL = "https://abcde12345xyz.supabase.co"  # Hãy giữ nguyên URL của bạn ở đây
SUPABASE_KEY = "eyJ..."                            # Hãy giữ nguyên API Key của bạn ở đây

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# --- CÁC HÀM XỬ LÝ DỮ LIỆU MẠNG ---
def load_data():
    try:
        response = supabase.table("transactions").select("*").order("date", desc=False).execute()
        if response.data and len(response.data) > 0:
            df = pd.DataFrame(response.data)
            if 'id' not in df.columns or df['id'].isnull().all():
                df['id'] = df.index.to_series()
            else:
                df['id'] = df['id'].fillna(df.index.to_series())
            return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
    return pd.DataFrame(columns=['id', 'date', 'type', 'category', 'amount', 'note'])

def save_transaction(date, t_type, category, amount, note):
    try:
        # Nhân với 1000 trước khi lưu vào Supabase để giữ đúng giá trị gốc
        real_amount = amount * 1000
        data = {"date": date, "type": t_type, "category": category, "amount": real_amount, "note": note}
        supabase.table("transactions").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi lưu giao dịch: {e}")
        return False

def update_transaction(date, t_type, category, amount, note, old_row):
    try:
        # Nhân với 1000 trước khi cập nhật vào Supabase
        real_amount = amount * 1000
        data = {"date": date, "type": t_type, "category": category, "amount": real_amount, "note": note}
        
        # Chuyển đổi amount của old_row về giá trị thực tế để tìm kiếm chính xác dòng cần sửa
        old_real_amount = float(old_row['amount_raw'])
        
        if 'id' in old_row and pd.notna(old_row['id']) and int(old_row['id']) > 1000: 
            supabase.table("transactions").update(data).eq("id", old_row['id']).execute()
        else:
            query = supabase.table("transactions").update(data).eq("date", old_row['date']).eq("category", old_row['category']).eq("amount", old_real_amount)
            if old_row['note']:
                query = query.eq("note", old_row['note'])
            query.execute()
        return True
    except Exception as e:
        st.error(f"Lỗi cập nhật: {e}")
        return False

def delete_transaction(old_row):
    try:
        old_real_amount = float(old_row['amount_raw'])
        if 'id' in old_row and pd.notna(old_row['id']) and int(old_row['id']) > 1000:
            supabase.table("transactions").delete().eq("id", old_row['id']).execute()
        else:
            query = supabase.table("transactions").delete().eq("date", old_row['date']).eq("category", old_row['category']).eq("amount", old_real_amount)
            if old_row['note']:
                query = query.eq("note", old_row['note'])
            query.execute()
        return True
    except Exception as e:
        st.error(f"Lỗi xóa: {e}")
        return False

def load_config():
    try:
        response = supabase.table("config_taichinh").select("*").execute()
        init_balance = 0.0
        custom_cats = []
        if response.data:
            for row in response.data:
                if row['key'] == 'init_balance':
                    init_balance = float(row['value'])
                elif row['key'] == 'custom_categories':
                    custom_cats = [c.strip() for c in row['value'].split(',') if c.strip()]
        return init_balance, custom_cats
    except:
        return 0.0, []

def save_config(init_balance, custom_cats):
    try:
        custom_cats_str = ",".join(custom_cats)
        supabase.table("config_taichinh").upsert([
            {'key': 'init_balance', 'value': str(init_balance)},
            {'key': 'custom_categories', 'value': custom_cats_str}
        ], on_conflict="key").execute()
        return True
    except Exception as e:
        st.error(f"Lỗi lưu cài đặt: {e}")
        return False

# Tải cấu hình ban đầu
init_balance, custom_categories = load_config()

# --- GIAO DIỆN APP STREAMLIT ---
st.set_page_config(page_title="Quản Lý Tài Chính Online", page_icon="💰", layout="centered")
st.title("💰 Ứng Dụng Quản Lý Tài Chính Online")

# --- PHẦN SIDEBAR (CÀI ĐẶT) ---
with st.sidebar:
    st.header("⚙️ Cài đặt hệ thống")
    # Số dư ban đầu nhập theo đơn vị x1000đ cho đồng bộ
    new_init_balance = st.number_input("Số tiền hiện có ban đầu (x1.000 VNĐ)", min_value=0.0, value=init_balance/1000.0, step=10.0, format="%.0f")
    
    st.subheader("➕ Thêm danh mục mới")
    new_cat = st.text_input("Tên danh mục muốn thêm", placeholder="Ví dụ: Tiền điện, Máy móc...")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Lưu cài đặt"):
            if new_cat and new_cat not in custom_categories:
                custom_categories.append(new_cat)
            if save_config(new_init_balance * 1000, custom_categories):
                st.success("Đã cập nhật mạng!")
                st.rerun()
            
    with col_btn2:
        if st.button("Xóa hết DM tự thêm"):
            if save_config(new_init_balance * 1000, []):
                st.warning("Đã xóa danh mục tự thêm!")
                st.rerun()

    if custom_categories:
        st.write("Danh mục bạn đã thêm:")
        for c in custom_categories:
            st.caption(f"- {c}")

default_chi = ["Ăn uống", "Di chuyển", "Mua sắm", "Nhà cửa", "Hóa đơn", "Khác"]
default_thu = ["Lương", "Thưởng", "Kinh doanh", "Khác"]

# --- CHIA TAB GIAO DIỆN ---
tab_main, tab_edit = st.tabs(["📝 Thêm & Xem Báo Cáo", "🛠️ Chỉnh Sửa / Xóa Giao Dịch"])

with tab_main:
    st.subheader("Thêm Giao Dịch Mới")
    with st.form(key='add_form', clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Ngày giao dịch", datetime.now(), key="add_date")
            t_type = st.selectbox("Loại giao dịch", ["Chi phí", "Thu nhập"], key="add_type")
        with col2:
            categories = (default_chi + custom_categories) if t_type == "Chi phí" else (default_thu + custom_categories)
            category = st.selectbox("Danh mục", categories, key="add_cat")
            # Người dùng nhập rút gọn (Ví dụ gõ 34 thay vì 34000)
            amount = st.number_input("Số tiền (x1.000 VNĐ) - Ví dụ: Nhập 34 cho 34.000đ", min_value=0.0, step=1.0, format="%.0f", key="add_amount")
            
        note = st.text_input("Ghi chú (không bắt buộc)", key="add_note")
        submit_button = st.form_submit_button(label='Lưu giao dịch')

    if submit_button:
        if amount > 0:
            if save_transaction(date.strftime("%Y-%m-%d"), t_type, category, amount, note):
                st.success("Đã lưu lên đám mây thành công!")
                st.rerun()
        else:
            st.error("Vui lòng nhập số tiền lớn hơn 0!")

    df = load_data()

    # --- HIỂN THỊ BÁO CÁO & BIỂU ĐỒ ---
df_expense = df[df['type'] == 'Chi phí']
        if not df_expense.empty:
            st.subheader("🍕 Cơ Cấu Chi Tiêu")
            expense_by_cat = df_expense.groupby('category')['amount'].sum()
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.pie(expense_by_cat, labels=expense_by_cat.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)

        # --- ĐOẠN THÊM MỚI: TỔNG THU CHI THEO TỪNG NGÀY ---
        st.markdown("---")
        st.subheader("📅 Tổng Hợp Thu Chi Theo Ngày (Đơn vị: k)")
        
        # Tạo bảng pivot table nhóm theo Ngày, tính tổng riêng cho Chi phí và Thu nhập
        df_daily = df.groupby(['date', 'type'])['amount'].sum().unstack(fill_value=0)
        
        # Đảm bảo bảng luôn có đủ 2 cột dù ngày đó chỉ có thu hoặc chỉ có chi
        if 'Chi phí' not in df_daily.columns:
            df_daily['Chi phí'] = 0.0
        if 'Thu nhập' not in df_daily.columns:
            df_daily['Thu nhập'] = 0.0
            
        # Tính số dư chênh lệch trong ngày (Thu - Chi)
        df_daily['Chênh lệch (Thu - Chi)'] = df_daily['Thu nhập'] - df_daily['Chi phí']
        
        # Sắp xếp ngày mới nhất lên đầu bảng cho dễ nhìn
        df_daily = df_daily.sort_index(ascending=False)
        
        # Định dạng lại tên cột và hiển thị số tiền rõ ràng
        df_daily = df_daily.rename(columns={'Chi phí': 'Tổng Chi (k)', 'Thu nhập': 'Tổng Thu (k)'})
        df_daily.index.names = ['Ngày']
        
        # Hiển thị bảng lên giao diện Streamlit
        st.dataframe(df_daily[['Tổng Thu (k)', 'Tổng Chi (k)', 'Chênh lệch (Thu - Chi)']], use_container_width=True)
        # --------------------------------------------------

        st.markdown("---")
        st.subheader("📜 Lịch Sử Giao Dịch (k = x1.000đ)")

# --- KHU VỰC CHỈNH SỬA & XÓA (TAB 2) ---
with tab_edit:
    st.subheader("🛠️ Sửa hoặc Xóa Giao Dịch Sai")
    df = load_data()
    
    if not df.empty and len(df) > 0:
        df_select = df.copy().iloc[::-1]
        df_select['amount_raw'] = pd.to_numeric(df_select['amount'], errors='coerce').fillna(0)
        df_select['amount_k'] = df_select['amount_raw'] / 1000.0
        
        df_select['display_text'] = df_select.apply(
            lambda r: f"{r['date']} | {r['type']} | {r['category']} | {float(r['amount_k']):,.0f}k", 
            axis=1
        )
        
        selected_option = st.selectbox("Chọn giao dịch bạn muốn sửa hoặc xóa:", df_select['display_text'].tolist())
        selected_row = df_select[df_select['display_text'] == selected_option].iloc[0]
        
        st.markdown("---")
        
        edit_date = st.date_input("Sửa Ngày", datetime.strptime(selected_row['date'], "%Y-%m-%d"), key="edit_date")
        edit_type = st.selectbox("Sửa Loại", ["Chi phí", "Thu nhập"], index=0 if selected_row['type'] == "Chi phí" else 1, key="edit_type")
        
        edit_categories = (default_chi + custom_categories) if edit_type == "Chi phí" else (default_thu + custom_categories)
        try:
            default_cat_index = edit_categories.index(selected_row['category'])
        except:
            default_cat_index = 0
            
        edit_cat = st.selectbox("Sửa Danh mục", edit_categories, index=default_cat_index, key="edit_cat")
        edit_amount = st.number_input("Sửa Số tiền (x1.000 VNĐ)", min_value=0.0, value=float(selected_row['amount_k']), step=1.0, format="%.0f", key="edit_amount")
        edit_note = st.text_input("Sửa Ghi chú", value=selected_row['note'] or "", key="edit_note")
        
        col_edit1, col_edit2 = st.columns(2)
        with col_edit1:
            if st.button("💾 CẬP NHẬT GIAO DỊCH", use_container_width=True, type="primary"):
                if edit_amount > 0:
                    if update_transaction(edit_date.strftime("%Y-%m-%d"), edit_type, edit_cat, edit_amount, edit_note, old_row=selected_row):
                        st.success("Đã cập nhật thay đổi thành công!")
                        st.rerun()
                else:
                    st.error("Số tiền sửa phải lớn hơn 0!")
                    
        with col_edit2:
            if st.button("🗑️ XÓA BỎ GIAO DỊCH NÀY", use_container_width=True):
                if delete_transaction(old_row=selected_row):
                    st.warning("Đã xóa giao dịch khỏi hệ thống!")
                    st.rerun()
    else:
        st.info("Chưa có dữ liệu nào để chỉnh sửa.")
