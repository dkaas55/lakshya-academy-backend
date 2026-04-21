import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import fetch_all_students, add_student, log_payment, fetch_all_transactions, update_student_record, delete_student
import os
import streamlit as st

st.set_page_config(page_title="Lakshya Academic Institute", layout="wide")

# --- TOAST & SESSION STATE NOTIFICATIONS ---
if "toast_msg" in st.session_state:
    st.toast(st.session_state.toast_msg, icon="✅")
    del st.session_state.toast_msg

# Initialize filter states so the "Clear" buttons work perfectly
if "tab1_name" not in st.session_state: st.session_state.tab1_name = ""
if "tab1_class" not in st.session_state: st.session_state.tab1_class = "All Classes"
if "tx_name" not in st.session_state: st.session_state.tx_name = ""
if "tx_class" not in st.session_state: st.session_state.tx_class = "All Classes"

def clear_tab1_filters():
    st.session_state.tab1_name = ""
    st.session_state.tab1_class = "All Classes"

def clear_tx_filters():
    st.session_state.tx_name = ""
    st.session_state.tx_class = "All Classes"

st.set_page_config(page_title="Lakshya ERP", layout="wide")

# ==========================================
# CUSTOM CSS ENGINE
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #ffffff !important; }
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* DESKTOP SIZES (Default) */
    h1 { font-size: 2.2rem !important; font-weight: 700 !important; }
    h2 { font-size: 1.8rem !important; font-weight: 700 !important; }
    p, label, span { font-size: 1rem !important; font-weight: 500 !important; }

    /* MOBILE SIZES (Applies only to screens smaller than 768px) */
    @media (max-width: 768px) {
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.1rem !important; }
        
        /* Smaller text for labels and paragraphs to fit more on screen */
        p, label, span, .stMarkdown {
            font-size: 0.9rem !important;
            font-weight: 500 !important;
        }

        /* Shrink padding so content hits the edges more */
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
        }

        /* Make buttons slightly shorter but still wide for thumbs */
        div.stButton > button:first-child {
            height: 2.5em !important;
            font-size: 0.9rem !important;
        }
    }
            /* Remove huge gaps at the top */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    /* Make buttons bigger for fingers to tap */
    div.stButton > button:first-child {
        width: 100%;
        height: 3em;
        margin-bottom: 10px;
    }

    /* Force data tables to be scrollable horizontally */
    .stDataFrame {
        width: 100%;
    }

    /* Make text inputs look better on small screens */
    input {
        font-size: 16px !important; 
    }

    .title-text { color: #1e1b6a; font-size: 48px; font-weight: bold; border-bottom: 4px solid #1e1b6a; padding-bottom: 5px; margin-top: 20px;}
    .metric-container { display: flex; justify-content: space-between; margin-top: 30px; margin-bottom: 20px; font-family: sans-serif; }
    .metric-box { display: flex; flex-direction: column; }
    .m-title { font-size: 16px; font-weight: 600; color: #000; }
    .m-val-black { font-size: 38px; font-weight: 700; color: #000; margin-top: -5px; }
    .m-val-green { font-size: 38px; font-weight: 700; color: #28a745; margin-top: -5px; }
    .m-val-red { font-size: 38px; font-weight: 700; color: #dc3545; margin-top: -5px; }
    hr { margin-top: 10px; margin-bottom: 20px; border: 1px solid #000; }
    div[data-baseweb="tab-list"] { gap: 15px; }
    div[data-baseweb="tab"] { 
        background-color: #5b54cc !important; 
        color: white !important; 
        border-radius: 25px !important; 
        padding: 8px 24px !important; 
        border: none !important; 
        font-weight: 600 !important;
    }
    div[data-baseweb="tab"][aria-selected="true"] { background-color: #3f399e !important; }
    
    .custom-table { width: 100%; border-collapse: collapse; font-family: sans-serif; margin-top: 10px; }
    .custom-table th { background-color: #5b54cc; color: white; padding: 12px; border: 1px solid #fff; text-align: left; }
    .custom-table td { background-color: #6a64d9; color: white; padding: 12px; border: 1px solid #fff; }
</style>
""", unsafe_allow_html=True)

def render_custom_table(dataframe):
    if dataframe.empty:
        st.info("No records found matching your search.")
    else:
        dataframe.insert(0, 'S No.', range(1, len(dataframe) + 1))
        html = dataframe.to_html(index=False, classes="custom-table", escape=False)
        st.markdown(html, unsafe_allow_html=True)

# ==========================================
# CALCULATION LOGIC
# ==========================================
students = fetch_all_students()
all_transactions = fetch_all_transactions()
today = datetime.now()

processed_data = []
student_dict = {} 

for s in students:
    if 'admission_id' not in s: 
        continue 
    
    join_date = s.get('joining_date', today)
    days_since_join = (today - join_date).days
    
    db_status = s.get('status', 'Active')
    s['db_status'] = db_status
    
    is_trial = days_since_join < 7
    
    if is_trial and db_status == 'Active':
        s['status'] = f"Trial ({7 - days_since_join} days left)"
        months_active = 0
        total_expected = 0
    else:
        s['status'] = db_status
        diff = relativedelta(today, join_date)
        months_active = (diff.years * 12) + diff.months + 1 
        total_expected = months_active * s.get('monthly_fee', 0)
        
    pending = total_expected - s.get('total_paid', 0)
    
    s['months_active'] = months_active
    s['current_pending'] = pending
    s['display_date'] = pd.to_datetime(join_date).strftime("%d %b %Y")
    s['display_fee'] = f"₹ {s.get('monthly_fee', 0):,.0f}"
    s['display_pending'] = f"₹ {pending:,.0f}"
    
    processed_data.append(s)
    student_dict[s['admission_id']] = s

active_students = [s for s in processed_data if s['status'] != 'Inactive']

total_students = len(active_students)
new_registrations = len([s for s in processed_data if s.get('joining_date', today).month == today.month and s.get('joining_date', today).year == today.year])
expected_monthly = sum(s.get('monthly_fee', 0) for s in processed_data if s['status'] == 'Active')
collected_this_month = sum(t['amount'] for t in all_transactions if t['date'].month == today.month and t['date'].year == today.year)
total_due = sum(s['current_pending'] for s in processed_data if s['current_pending'] > 0)

class_options = ["All Classes"] + [str(i) for i in range(4, 13)]

# ==========================================
# HEADER
# ==========================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
        
with col_title:
    st.markdown('<div class="title-text">Lakshya Academic Institute</div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="metric-container">
    <div class="metric-box"><span class="m-title">Total Active Students</span><span class="m-val-black">{total_students}</span></div>
    <div class="metric-box"><span class="m-title">New Registrations</span><span class="m-val-black">{new_registrations}</span></div>
    <div class="metric-box"><span class="m-title">Expected Revenue</span><span class="m-val-black">₹ {expected_monthly:,.0f}</span></div>
    <div class="metric-box"><span class="m-title" style="color: #28a745;">Collected</span><span class="m-val-green">₹ {collected_this_month:,.0f}</span></div>
    <div class="metric-box"><span class="m-title" style="color: #dc3545;">Total pending due</span><span class="m-val-red">₹ {total_due:,.0f}</span></div>
</div>
<hr>
""", unsafe_allow_html=True)

# ==========================================
# TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Student Details", "Fee Submission", "New Registration", "Pending Fees", "Transaction Details"
])

# --- TAB 1: STUDENT DETAILS ---
with tab1:
    if processed_data:
        c_search_area, c_manage = st.columns([4, 1])
        
        with c_search_area:
            with st.form("tab1_search_form", border=False):
                # Added an extra column for the Clear Button
                f_c1, f_c2, f_c3, f_c4 = st.columns([3, 2, 1, 1])
                with f_c1:
                    name_query = st.text_input("Search Name", placeholder="Search by Name...", key="tab1_name", label_visibility="collapsed")
                with f_c2:
                    class_filter = st.selectbox("Filter Class", options=class_options, key="tab1_class", label_visibility="collapsed")
                with f_c3:
                    search_clicked = st.form_submit_button("🔍 Search", use_container_width=True)
                with f_c4:
                    clear_clicked = st.form_submit_button("❌ Clear", on_click=clear_tab1_filters, use_container_width=True)
                    
        with c_manage:
            with st.popover("🛠️ Manage Student", use_container_width=True):
                st.write("**Update / Delete Records**")
                
                m_class_filter = st.selectbox("Filter by Class", options=class_options, key="m_class")
                m_options = [s for s in processed_data if m_class_filter == "All Classes" or s['class_name'] == m_class_filter]
                
                manage_student = st.selectbox(
                    "Search Student", 
                    options=m_options, 
                    format_func=lambda x: f"{x['name']} ({x['status']})",
                    index=None,
                    placeholder="Type name to search..."
                )
                
                if manage_student:
                    current_idx = 0 if manage_student['db_status'] == 'Active' else 1
                    new_status = st.selectbox("Status", ["Active", "Inactive"], index=current_idx)
                    
                    current_fee = int(manage_student.get('monthly_fee', 0))
                    new_fee = st.number_input("Monthly Fee (₹)", min_value=0, value=current_fee)
                    
                    if st.button("Save Changes", use_container_width=True):
                        update_student_record(manage_student['admission_id'], new_status, new_fee)
                        st.session_state.toast_msg = f"Updated records for {manage_student['name']}!"
                        st.rerun()
                        
                    st.divider()
                    
                    if st.button("🗑️ Delete Record", type="primary", use_container_width=True):
                        delete_student(manage_student['admission_id'])
                        st.session_state.toast_msg = f"Permanently deleted {manage_student['name']} from the database."
                        st.rerun()
        
        df = pd.DataFrame(processed_data)
        display_df = df[['name', 'class_name', 'parent_phone', 'display_date', 'display_fee', 'display_pending', 'status']]
        display_df.columns = ['Student Name', 'Class', 'Mobile No.', 'Joining Date', 'Monthly Fee', 'Pending Fee', 'Status']
        
        if name_query:
            display_df = display_df[display_df['Student Name'].str.contains(name_query, case=False, na=False)]
        if class_filter != "All Classes":
            display_df = display_df[display_df['Class'].astype(str) == class_filter]
            
        render_custom_table(display_df)
    else:
        st.info("No students found.")

# --- TAB 2: FEE SUBMISSION ---
with tab2:
    if active_students:
        st.subheader("Log a Payment")
        
        f_c1, f_c2 = st.columns([1, 3])
        with f_c1:
            fee_class_filter = st.selectbox("Select Class", options=class_options, key="fee_class")
        with f_c2:
            fee_options = [s for s in active_students if fee_class_filter == "All Classes" or s['class_name'] == fee_class_filter]
            
            selected_student = st.selectbox(
                "Search Active Student", 
                options=fee_options,
                format_func=lambda x: f"{x['name']} | Class {x['class_name']} | Due: ₹{x['current_pending']}",
                index=None,
                placeholder="Type student name to search..."
            )
            
        if selected_student:
            with st.form("payment_form", clear_on_submit=True):
                pc1, pc2 = st.columns(2)
                amt = pc1.number_input("Amount Paid Today (₹)", min_value=0, value=max(0, int(selected_student['current_pending'])))
                mode = pc2.selectbox("Payment Mode", ["Cash", "UPI", "Bank Transfer"])
                
                if st.form_submit_button("Confirm & Log Payment"):
                    log_payment(selected_student['admission_id'], amt, mode)
                    st.session_state.toast_msg = f"Logged ₹{amt} for {selected_student['name']}!"
                    st.rerun()
    else:
        st.info("No active students available for fee submission.")

# --- TAB 3: NEW REGISTRATION ---
with tab3:
    with st.form("new_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        r_name = col1.text_input("Student Name")
        r_phone = col2.text_input("Parent Phone Number")
        col3, col4 = st.columns(2)
        r_class = col3.selectbox("Class", [str(i) for i in range(4, 13)])
        r_fee = col4.number_input("Monthly Fee Agreed (₹)", min_value=0)
        r_date = st.date_input("Joining Date")
        
        if st.form_submit_button("Register Student"):
            if r_name and r_phone:
                new_id = add_student(r_name, r_class, r_phone, r_fee, r_date)
                st.session_state.toast_msg = f"{r_name} successfully registered and is in Trial!"
                st.rerun()
            else:
                st.error("Name and Phone are required.")

# --- TAB 4: PENDING FEES (Defaulters List) ---
with tab4:
    defaulters = [s for s in processed_data if s['current_pending'] > 0]
    if defaulters:
        df_def = pd.DataFrame(defaulters)
        df_def = df_def.sort_values(by='current_pending', ascending=False)
        
        display_def = df_def[['name', 'class_name', 'parent_phone', 'display_pending']]
        display_def.columns = ['Student Name', 'Class', 'Mobile No.', 'Total Pending Due']
        
        render_custom_table(display_def)
    else:
        st.success("Hooray! No pending fees currently.")

# --- TAB 5: TRANSACTION DETAILS ---
with tab5:
    if all_transactions:
        with st.form("tab5_search_form", border=False):
            # Added Clear button here as well
            c_tx_search, c_tx_filter, c_tx_btn, c_tx_clear = st.columns([3, 2, 1, 1])
            with c_tx_search:
                tx_name_query = st.text_input("Search Name", placeholder="Search by Name...", key="tx_name", label_visibility="collapsed")
            with c_tx_filter:
                tx_class_filter = st.selectbox("Filter Class", options=class_options, key="tx_class", label_visibility="collapsed")
            with c_tx_btn:
                tx_search_clicked = st.form_submit_button("🔍 Search", use_container_width=True)
            with c_tx_clear:
                tx_clear_clicked = st.form_submit_button("❌ Clear", on_click=clear_tx_filters, use_container_width=True)
        
        tx_list = []
        for t in all_transactions:
            s_info = student_dict.get(t['admission_id'], {})
            tx_list.append({
                'Receipt No.': t['receipt_number'],
                'Date': t['date'].strftime("%d %b %Y, %I:%M %p"),
                'Student Name': s_info.get('name', 'Unknown/Deleted Student'),
                'Class': str(s_info.get('class_name', 'N/A')),
                'Amount Paid': f"₹ {t['amount']:,.0f}",
                'Mode': t['mode']
            })
            
        df_tx = pd.DataFrame(tx_list)
        df_tx = df_tx.iloc[::-1] 
        
        if tx_name_query:
            df_tx = df_tx[df_tx['Student Name'].str.contains(tx_name_query, case=False, na=False)]
        if tx_class_filter != "All Classes":
            df_tx = df_tx[df_tx['Class'].astype(str) == tx_class_filter]
            
        render_custom_table(df_tx)
    else:
        st.info("No transactions logged yet.")