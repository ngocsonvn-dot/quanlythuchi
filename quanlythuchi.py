import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from supabase import create_client, Client

# --- CẤU HÌNH KẾT NỐI ĐÁM MÂY SUPABASE ---
SUPABASE_URL = "https://ovzcqsbfrqkhidubwegy.supabase.co"  # <--- Hãy điền lại URL của bạn vào đây
SUPABASE_KEY = "sb_publishable_pwfUSnNT6NzulpzZoiNrbg_9yV2qZQJ"                            # <--- Hãy điền lại API Key của bạn vào đây

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
        real_amount = amount * 1000
        data = {"date": date, "type": t_type, "category": category, "amount": real_amount, "note": note}
        supabase.table("transactions").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi lưu giao dịch: {e}")
        return False

def update_transaction(date, t_type, category, amount, note, old_row):
    try:
        real_amount = amount * 1000
        data = {"date": date, "type": t_type, "category": category, "amount": real_amount, "note": note}
        old_real_amount = float(old_row['amount_raw'])
        
        try:
            supabase.table("transactions").update(data).eq("id", int(old_row['id'])).execute()
        except:
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
        try:
            t_id = int(old_row['id'])
            supabase.table("transactions").delete().eq("id", t_id).execute()
        except:
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

# --- PHẦN SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cài đặt hệ thống")
    new_init_balance = st.number_input("Số tiền hiện có ban đầu (x1.000 VNĐ)", min_value=0.0, value=init_balance/1000.0, step=10.0, format="%.0f")
    st.subheader("➕ Thêm danh mục mới")
    new_cat = st.text_input("Tên danh mục muốn thêm", placeholder="Ví dụ: Tiền điện...")
    
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

# --- PHÂN CHIA DANH MỤC THEO 2 MỤC LỚN ---
# Các danh mục mặc định được định hình theo nhóm rõ ràng
danh_muc_he_thong = {
    "Chi tiêu cá nhân": ["Ăn uống", "Mua sắm cá nhân", "Nhà cửa & Sinh hoạt", "Di chuyển", "Khác (Cá nhân)"],
    "Chi tiêu phục vụ kinh doanh": ["Mua vật tư / Nguyên liệu", "Sửa chữa máy móc", "Hóa đơn xưởng / Điện sản xuất", "Vận chuyển / Giao hàng", "Khác (Kinh doanh)"],
    "Thu nhập": ["Lương", "Doanh thu kinh doanh", "Thưởng", "Khác (Thu nhập)"]
}

# --- CHIA TAB GIAO DIỆN ---
tab_main, tab_edit = st.tabs(["📝 Thêm & Xem Báo Cáo", "🛠️ Chỉnh Sửa / Xóa Giao Dịch"])

with tab_main:
    st.subheader("Thêm Giao Dịch Mới")
    with st.form(key='add_form', clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Ngày giao dịch", datetime.now(), key="add_date")
            # Chọn loại lớn trước
            t_group = st.selectbox("Mục lớn", ["Chi tiêu cá nhân", "Chi tiêu phục vụ kinh doanh", "Thu nhập"], key="add_group")
        with col2:
            # Lấy danh sách danh mục tương ứng với Mục lớn đã chọn + kết hợp danh mục tự thêm
            categories = danh_muc_he_thong[t_group] + custom_categories
            category = st.selectbox("Danh mục cụ thể", categories, key="add_cat")
            amount = st.number_input("Số tiền (x1.000 VNĐ) - Ví dụ: Nhập 34 cho 34.000đ", min_value=0.0, step=1.0, format="%.0f", key="add_amount")
            
        note = st.text_input("Ghi chú (không bắt buộc)", key="add_note")
        submit_button = st.form_submit_button(label='Lưu giao dịch')

    if submit_button:
        if amount > 0:
            # Lưu loại giao dịch: Nếu là Thu nhập thì lưu "Thu nhập", còn lại lưu là "Chi phí" để tính toán, ghi chú/danh mục sẽ giữ vai trò phân loại lớn
            t_type = "Thu nhập" if t_group == "Thu nhập" else "Chi phí"
            # Lưu tên Mục lớn kèm vào danh mục hoặc ghi chú để sau này truy vết thu chi
            actual_category = f"[{t_group}] {category}"
            
            if save_transaction(date.strftime("%Y-%m-%d"), t_type, actual_category, amount, note):
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
        df['amount'] = df['amount_raw'] / 1000.0
        
        # Hàm hỗ trợ phân tách Mục lớn để xử lý báo cáo
        def parse_group(cat):
            if "[Chi tiêu cá nhân]" in str(cat): return "Cá nhân"
            if "[Chi tiêu phục vụ kinh doanh]" in str(cat): return "Kinh doanh"
            return "Khác"

        df['Muc_Lon'] = df['category'].apply(parse_group)
        # Làm sạch tên danh mục hiển thị (bỏ phần tiền tố [Mục lớn])
        df['Danh_Muc_Sạch'] = df['category'].apply(lambda x: str(x).split('] ')[-1] if ']' in str(x) else str(x))

        total_income = df[df['type'] == 'Thu nhập']['amount'].sum()
        total_expense = df[df['type'] == 'Chi phí']['amount'].sum()
        balance = (init_balance / 1000.0) + total_income - total_expense

        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng Thu nhập", f"{total_income:,.0f} k")
        c2.metric("Tổng Chi tiêu", f"{total_expense:,.0f} k", delta_color="inverse")
        c3.metric("Số Dư Hiện Tại", f"{balance:,.0f} k")

        # Tách biệt số liệu 2 mục chi tiêu lớn để hiển thị trực quan
        df_expense = df[df['type'] == 'Chi phí']
        if not df_expense.empty:
            st.markdown("---")
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                df_ca_nhan = df_expense[df_expense['Muc_Lon'] == 'Cá nhân']
                st.subheader("🛒 Chi Tiêu Cá Nhân")
                if not df_ca_nhan.empty:
                    exp_cn = df_ca_nhan.groupby('Danh_Muc_Sạch')['amount'].sum()
                    fig, ax = plt.subplots(figsize=(5, 5))
                    ax.pie(exp_cn, labels=exp_cn.index, autopct='%1.1f%%', startangle=90)
                    ax.axis('equal')
                    st.pyplot(fig)
                    st.write(f"**Tổng chi cá nhân:** {df_ca_nhan['amount'].sum():,.0f} k")
                else:
                    st.info("Chưa có dữ liệu chi tiêu cá nhân.")
                    
            with col_chart2:
                df_kinh_doanh = df_expense[df_expense['Muc_Lon'] == 'Kinh doanh']
                st.subheader("🏭 Phục Vụ Kinh Doanh")
                if not df_kinh_doanh.empty:
                    exp_kd = df_kinh_doanh.groupby('Danh_Muc_Sạch')['amount'].sum()
                    fig, ax = plt.subplots(figsize=(5, 5))
                    ax.pie(exp_kd, labels=exp_kd.index, autopct='%1.1f%%', startangle=90)
                    ax.axis('equal')
                    st.pyplot(fig)
                    st.write(f"**Tổng chi kinh doanh:** {df_kinh_doanh['amount'].sum():,.0f} k")
                else:
                    st.info("Chưa có dữ liệu chi kinh doanh.")

        # --- BẢNG TỔNG HỢP THEO NGÀY ---
        st.markdown("---")
        st.subheader("📅 Tổng Hợp Thu Chi Theo Ngày (Đơn vị: k)")
        
        # Nhóm dữ liệu theo ngày và mục phân loại cụ thể
        df_daily_raw = df.copy()
        df_daily_raw['Loai_Phan_Chia'] = df_daily_raw.apply(
            lambda r: "Tổng Thu" if r['type'] == 'Thu nhập' else f"Chi {r['Muc_Lon']}", axis=1
        )
        
        df_daily = df_daily_raw.groupby(['date', 'loai_phan_chia' if 'loai_phan_chia' in df_daily_raw else 'Loai_Phan_Chia'])['amount'].sum().unstack(fill_value=0)
        
        for col in ['Tổng Thu', 'Chi Cá nhân', 'Chi Kinh doanh']:
            if col not in df_daily.columns:
                df_daily[col] = 0.0
                
        df_daily['Chênh lệch dòng tiền'] = df_daily['Tổng Thu'] - df_daily['Chi Cá nhân'] - df_daily['Chi Kinh doanh']
        df_daily = df_daily.sort_index(ascending=False)
        df_daily.index.names = ['Ngày']
        
        st.dataframe(df_daily[['Tổng Thu', 'Chi Cá nhân', 'Chi Kinh doanh', 'Chênh lệch dòng tiền']], use_container_width=True)

        # --- LỊCH SỬ GIAO DỊCH ---
        st.markdown("---")
        st.subheader("📜 Lịch Sử Giao Dịch Chi Tiết (k = x1.000đ)")
        df_display = df.copy().iloc[::-1]
        df_display['Loại mục'] = df_display['Muc_Lon'].map({'Cá nhân': 'Cá nhân 👤', 'Kinh doanh': 'Kinh doanh 🏭', 'Khác': 'Thu nhập 💰'})
        df_display = df_display.rename(columns={'date': 'Ngày', 'Danh_Muc_Sạch': 'Danh mục', 'amount': 'Số tiền (k)', 'note': 'Ghi chú'})
        st.dataframe(df_display[['Ngày', 'Loại mục', 'Danh mục', 'Số tiền (k)', 'Ghi chú']], use_container_width=True)
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng Thu nhập", "0 k")
        c2.metric("Tổng Chi tiêu", "0 k")
        c3.metric("Số Dư Hiện Tại", f"{init_balance/1000.0:,.0f} k")
        st.info("Chưa có giao dịch phát sinh trên hệ thống đám mây.")

# --- KHU VỰC CHỈNH SỬA & XÓA (TAB 2) ---
with tab_edit:
    st.subheader("🛠️ Sửa hoặc Xóa Giao Dịch Sai")
    df = load_data()
    
    if not df.empty and len(df) > 0:
        df_select = df.copy().iloc[::-1]
        df_select['amount_raw'] = pd.to_numeric(df_select['amount'], errors='coerce').fillna(0)
        df_select['amount_k'] = df_select['amount_raw'] / 1000.0
        
        df_select['display_text'] = df_select.apply(
            lambda r: f"{r['date']} | {str(r['category']).split('] ')[-1] if ']' in str(r['category']) else r['category']} | {float(r['amount_k']):,.0f}k", 
            axis=1
        )
        
        selected_option = st.selectbox("Chọn giao dịch bạn muốn sửa hoặc xóa:", df_select['display_text'].tolist())
        selected_row = df_select[df_select['display_text'] == selected_option].iloc[0]
        
        st.markdown("---")
        
        edit_date = st.date_input("Sửa Ngày", datetime.strptime(selected_row['date'], "%Y-%m-%d"), key="edit_date")
        edit_group = st.selectbox("Sửa Mục lớn", ["Chi tiêu cá nhân", "Chi tiêu phục vụ kinh doanh", "Thu nhập"], 
                                  index=0 if "[Chi tiêu cá nhân]" in str(selected_row['category']) else (1 if "[Chi tiêu phục vụ kinh doanh]" in str(selected_row['category']) else 2), key="edit_group")
        
        raw_cat = str(selected_row['category']).split('] ')[-1] if ']' in str(selected_row['category']) else str(selected_row['category'])
        edit_categories = danh_muc_he_thong[edit_group] + custom_categories
        try:
            default_cat_index = edit_categories.index(raw_cat)
        except:
            default_cat_index = 0
            
        edit_cat = st.selectbox("Sửa Danh mục", edit_categories, index=default_cat_index, key="edit_cat")
        edit_amount = st.number_input("Sửa Số tiền (x1.000 VNĐ)", min_value=0.0, value=float(selected_row['amount_k']), step=1.0, format="%.0f", key="edit_amount")
        edit_note = st.text_input("Sửa Ghi chú", value=selected_row['note'] or "", key="edit_note")
        
        col_edit1, col_edit2 = st.columns(2)
        with col_edit1:
            if st.button("💾 CẬP NHẬT GIAO DỊCH", use_container_width=True, type="primary"):
                if edit_amount > 0:
                    actual_edit_type = "Thu nhập" if edit_group == "Thu nhập" else "Chi phí"
                    actual_edit_cat = f"[{edit_group}] {edit_cat}"
                    if update_transaction(edit_date.strftime("%Y-%m-%d"), actual_edit_type, actual_edit_cat, edit_amount, edit_note, old_row=selected_row):
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
