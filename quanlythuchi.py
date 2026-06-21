import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from supabase import create_client, Client

# --- CẤU HÌNH KẾT NỐI ĐÁM MÂY SUPABASE ---
SUPABASE_URL = "https://ovzcqsbfrqkhidubwegy.supabase.co"
SUPABASE_KEY = "sb_publishable_pwfUSnNT6NzulpzZoiNrbg_9yV2qZQJ"


# Khởi tạo kết nối vĩnh viễn với database mạng
@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()


# --- CÁC HÀM XỬ LÝ DỮ LIỆU MẠNG ---
def load_data():
    try:
        response = supabase.table("transactions").select("*").order("date", descending=False).execute()
        if response.data and len(response.data) > 0:
            df = pd.DataFrame(response.data)
            # Đổi tên cột từ tiếng Anh trên mạng sang tiếng Việt hiển thị trên App
            df = df.rename(columns={
                'date': 'Ngày',
                'type': 'Loại',
                'category': 'Danh mục',
                'amount': 'Số tiền',
                'note': 'Ghi chú'
            })
            return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}")
    return pd.DataFrame(columns=['Ngày', 'Loại', 'Danh mục', 'Số tiền', 'Ghi chú'])


def save_transaction(date, t_type, category, amount, note):
    try:
        data = {
            "date": date,
            "type": t_type,
            "category": category,
            "amount": amount,
            "note": note
        }
        supabase.table("transactions").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi lưu giao dịch: {e}")
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
        # Xóa cấu hình cũ để ghi đè cấu hình mới
        supabase.table("config_taichinh").delete().neq("key", "empty").execute()
        # Chèn cấu hình mới vào database
        supabase.table("config_taichinh").insert([
            {'key': 'init_balance', 'value': str(init_balance)},
            {'key': 'custom_categories', 'value': custom_cats_str}
        ]).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi lưu cài đặt: {e}")
        return False


# Tải cấu hình mạng ban đầu
init_balance, custom_categories = load_config()

# --- GIAO DIỆN APP STREAMLIT ---
st.set_page_config(page_title="Quản Lý Tài Chính Online", page_icon="💰", layout="centered")
st.title("💰 Ứng Dụng Quản Lý Tài Chính Online")

# --- PHẦN TÌNH CHỈNH CẤU HÌNH (CÀI ĐẶT SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Cài đặt hệ thống")
    new_init_balance = st.number_input("Số tiền hiện có ban đầu (VNĐ)", min_value=0.0, value=init_balance, step=10000.0,
                                       format="%.0f")

    st.subheader("➕ Thêm danh mục mới")
    new_cat = st.text_input("Tên danh mục muốn thêm", placeholder="Ví dụ: Tiền điện, Máy móc...")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Lưu cài đặt"):
            if new_cat and new_cat not in custom_categories:
                custom_categories.append(new_cat)
            if save_config(new_init_balance, custom_categories):
                st.success("Đã cập nhật mạng!")
                st.rerun()

    with col_btn2:
        if st.button("Xóa hết DM tự thêm"):
            if save_config(new_init_balance, []):
                st.warning("Đã xóa danh mục tự thêm!")
                st.rerun()

    if custom_categories:
        st.write("Danh mục bạn đã thêm:")
        for c in custom_categories:
            st.caption(f"- {c}")

# --- PHẦN FORM NHẬP LIỆU ---
st.subheader("📝 Thêm Giao Dịch Mới")
with st.form(key='add_form', clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Ngày giao dịch", datetime.now())
        t_type = st.selectbox("Loại giao dịch", ["Chi phí", "Thu nhập"])
    with col2:
        default_chi = ["Ăn uống", "Di chuyển", "Mua sắm", "Nhà cửa", "Hóa đơn", "Khác"]
        default_thu = ["Lương", "Thưởng", "Kinh doanh", "Khác"]
        categories = (default_chi + custom_categories) if t_type == "Chi phí" else (default_thu + custom_categories)

        category = st.selectbox("Danh mục", categories)
        amount = st.number_input("Số tiền (VNĐ)", min_value=0.0, step=1000.0, format="%.0f")

    note = st.text_input("Ghi chú (không bắt buộc)")
    submit_button = st.form_submit_button(label='Lưu giao dịch')

if submit_button:
    if amount > 0:
        success = save_transaction(date.strftime("%Y-%m-%d"), t_type, category, amount, note)
        if success:
            st.success("Đã lưu lên đám mây thành công!")
            st.rerun()
    else:
        st.error("Vui lòng nhập số tiền lớn hơn 0!")

df = load_data()

# --- PHẦN HIỂN THỊ BÁO CÁO & BIỂU ĐỒ ---
st.markdown("---")
st.subheader("📊 Tổng Quan Tài Chính")

df['Số tiền'] = pd.to_numeric(df['Số tiền'], errors='coerce').fillna(0)
total_income = df[df['Loại'] == 'Thu nhập']['Số tiền'].sum()
total_expense = df[df['Loại'] == 'Chi phí']['Số tiền'].sum()
balance = init_balance + total_income - total_expense

c1, c2, c3 = st.columns(3)
c1.metric("Tổng Thu thêm", f"{total_income:,.0f} đ")
c2.metric("Tổng Chi thêm", f"{total_expense:,.0f} đ", delta_color="inverse")
c3.metric("Số Dư Hiện Tại", f"{balance:,.0f} đ")

if not df.empty and len(df) > 0:
    df_expense = df[df['Loại'] == 'Chi phí']
    if not df_expense.empty:
        st.subheader("🍕 Cơ Cấu Chi Tiêu")
        expense_by_cat = df_expense.groupby('Danh mục')['Số tiền'].sum()

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.pie(expense_by_cat, labels=expense_by_cat.index, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)

    st.markdown("---")
    st.subheader("📜 Lịch Sử Giao Dịch")
    df_display = df.copy().iloc[::-1]
    df_display['Số tiền'] = df_display['Số tiền'].apply(lambda x: f"{x:,.0f}")
    st.dataframe(df_display, use_container_width=True)
else:
    st.info("Chưa có giao dịch phát sinh trên hệ thống đám mây.")
