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
    st.markdown("---")
    st.subheader("📊 Tổng Quan Tài Chính (Đơn vị: x1.000đ)")

    if not df.empty and 'amount' in df.columns:
        df['amount_raw'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
        # Quy đổi tất cả hiển thị ra đơn vị nghìn đồng
        df['amount'] = df['amount_raw'] / 1000.0
        
        total_income = df[df['type'] == 'Thu nhập']['amount'].sum()
        total_expense = df[df['type'] == 'Chi phí']['amount'].sum()
        balance = (init_balance / 1000.0) + total_income - total_expense

        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng Thu thêm", f"{total_income:,.0f} k")
        c2.metric("Tổng Chi thêm", f"{total_expense:,.0f} k", delta_color="inverse")
        c3.metric("Số Dư Hiện Tại", f"{balance:,.0f} k")

        df_expense = df[df['type'] == 'Chi phí']
        if not df_expense.empty:
            st.subheader("🍕 Cơ Cấu Chi Tiêu")
            expense_by_cat = df_expense.groupby('category')['amount'].sum()
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.pie(expense_by_cat, labels=expense_by_cat.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)

        # --- ĐOẠN TỔNG HỢP THEO NGÀY ---
        st.markdown("---")
        st.subheader("📅 Tổng Hợp Thu Chi Theo Ngày (Đơn vị: k)")
        
        df_daily = df.groupby(['date', 'type'])['amount'].sum().unstack(fill_value=0)
        
        if 'Chi phí' not in df_daily.columns:
            df_daily['Chi phí'] = 0.0
        if 'Thu nhập' not in df_daily.columns:
            df_daily['Thu nhập'] = 0.0
            
        df_daily['Chênh lệch (Thu - Chi)'] = df_daily['Thu nhập'] - df_daily['Chi phí']
        df_daily = df_daily.sort_index(ascending=False)
        df_daily = df_daily.rename(columns={'Chi phí': 'Tổng Chi (k)', 'Thu nhập': 'Tổng Thu (k)'})
        df_daily.index.names = ['Ngày']
        
        st.dataframe(df_daily[['Tổng Thu (k)', 'Tổng Chi (k)', 'Chênh lệch (Thu - Chi)']], use_container_width=True)

        st.markdown("---")
        st.subheader("📜 Lịch Sử Giao Dịch (k = x1.000đ)")
        df_display = df.copy().iloc[::-1]
        df_display = df_display.rename(columns={'date': 'Ngày', 'type': 'Loại', 'category': 'Danh mục', 'amount': 'Số tiền (k)', 'note': 'Ghi chú'})
        st.dataframe(df_display[['Ngày', 'Loại', 'Danh mục', 'Số tiền (k)', 'Ghi chú']], use_container_width=True)
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng Thu thêm", "0 k")
        c2.metric("Tổng Chi thêm", "0 k")
        c3.metric("Số Dư Hiện Tại", f"{init_balance/1000.0:,.0f} k")
        st.info("Chưa có giao dịch phát sinh trên hệ thống đám mây.")
