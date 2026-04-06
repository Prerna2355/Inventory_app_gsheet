import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import io

# ---------- CONFIG ----------
PAGE_TITLE = "Inventory Update"

# ---------- NORMALIZATION ----------
def normalize_text(text):
    if isinstance(text, str):
        return text.strip().title()
    return text

# ---------- GOOGLE SHEETS SETUP ----------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
import json
import os
creds_dict = json.loads(os.environ["gcp_service_account"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("Inventory_Sheet").sheet1

# ---------- FUNCTIONS ----------
def fetch_inventory():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # Normalize key columns
    for col in ["Operator Name","Area","Property Category", "Property Type", "Property Address","Owner/Builder name","BHK", "Comments"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.title()

    return df


def insert_item(Date,Operator_Name,Property_Category, Property_Type, Area,Property_Address,Unit_No_Floor_No,BHK,Owner_Builder_name,Owner_Builder_number,Size, Price,Cheque,Comments):

    current_data = sheet.get_all_records()
    new_id = len(current_data) + 1

    sheet.append_row([
        new_id,
        Date,
        normalize_text(Operator_Name),
        normalize_text(Property_Category),
        normalize_text(Property_Type),
        normalize_text(Area),
        normalize_text(Property_Address),
        normalize_text(Unit_No_Floor_No),
        normalize_text(BHK),
        normalize_text(Owner_Builder_name),
        normalize_text(Owner_Builder_number),
        normalize_text(Size),
        normalize_text(Price),
        normalize_text(Cheque),
        normalize_text(Comments)
    ])


def update_item(row_number, price, Comments):
    sheet.update_cell(row_number, 10, normalize_text(price))
    sheet.update_cell(row_number, 15, normalize_text(Comments))


def delete_item(row_number):
    sheet.delete_rows(row_number)


# ---------- SESSION ----------
if "df" not in st.session_state:
    st.session_state.df = fetch_inventory()

if "form_reset" not in st.session_state:   
    st.session_state.form_reset = 0

# ---------- UI ----------
st.title(PAGE_TITLE)
st.write("Lead Management System.")

df = st.session_state.df

st.metric("Total Items", len(df))
st.divider()

menu = st.sidebar.radio(
    "Navigation",
    ["Home", "Add Item", "View items", "Edit / Delete"]
)

# ---------- HOME ----------
if menu == "Home":
    st.subheader("Recent Items")
    if df.empty:
        st.info("No inventory yet.")
    else:
        st.dataframe(df.tail(10), use_container_width=True)

# ---------- ADD ITEM ----------
elif menu == "Add Item":
    st.subheader("➕ Add New Lead")

    Categories = ["Residential Land/Plot", "Kothi/Villa", "Builder floor",
                  "Appartement/Flats", "Old/New Floors", "1RK/Studio Apartements", "Commercial/Shops"]

    Property_Types = ["Rent", "Sale", "Resale"]

    submit= False
    clear= False
    with st.form(f"add_form_{st.session_state.form_reset}"):
        date = st.text_input("Date",key=f"date_{st.session_state.form_reset}")
        op_name = st.text_input("Operator_Name",key=f"op_name_{st.session_state.form_reset}")
        category = st.selectbox("Property_Category", Categories, key=f"category_{st.session_state.form_reset}")
        ptype = st.selectbox("Property_Type", Property_Types, key=f"ptype_{st.session_state.form_reset}")
        area = st.text_input("Area", key=f"area_{st.session_state.form_reset}")
        address = st.text_input("Property_Address", key=f"address_{st.session_state.form_reset}")
        unit_no = st.text_input("Unit_No_Floor_No", key=f"unit_no_{st.session_state.form_reset}")
        bhk = st.text_input("BHK",key=f"bhk_{st.session_state.form_reset}")
        size = st.text_input("Size", key=f"size_{st.session_state.form_reset}")
        price = st.text_input("Price", key=f"price_{st.session_state.form_reset}")
        cheque = st.text_input("Cheque", key=f"cheque_{st.session_state.form_reset}")
        builder_name = st.text_input("Owner_Builder_name", key=f"builder_name_{st.session_state.form_reset}")
        builder_no = st.text_input("Owner_Builder_number", key=f"builder_no_{st.session_state.form_reset}")
        comments = st.text_area("Comments", key=f"comments_{st.session_state.form_reset}")
        
        col1, col2 = st.columns(2)

        with col1:
            submit = st.form_submit_button("💾 Save")
        
        with col2:
            clear = st.form_submit_button("🧹 Clear")
                #submit = st.form_submit_button("Save")
    if submit:
        insert_item(date, op_name, category, ptype, area, address, unit_no, bhk,
                    size, price, cheque, builder_name, builder_no, comments)
    
        st.session_state.df = fetch_inventory()
        st.success("✅ Lead added successfully")
        st.session_state.form_reset += 1
        st.rerun()
    
    
    # 🔘 Clear Form Button
    if clear:
        st.session_state.form_reset += 1
        st.rerun()

# ---------- VIEW ITEMS ----------
elif menu == "View items":
    st.subheader("Inventory List")

    # 🔍 Filters
    search_owner = st.text_input("Search by Owner Name")

    area_filter = st.selectbox(
        "Filter by Area",
        ["All"] + sorted(df["Area"].dropna().unique().tolist()) if not df.empty else ["All"]
    )

    category_filter = st.selectbox(
        "Filter by Category",
        ["All"] + sorted(df["Property_Category"].dropna().unique().tolist()) if not df.empty else ["All"]
    )

    # Apply filters
    filtered_df = df.copy()

    if area_filter != "All":
        filtered_df = filtered_df[filtered_df["Area"] == area_filter]

    if category_filter != "All":
        filtered_df = filtered_df[filtered_df["Property_Category"] == category_filter]

    if search_owner:
        filtered_df = filtered_df[
            filtered_df["Owner_Builder_name"].str.lower().str.contains(search_owner.lower())
        ]

    st.dataframe(filtered_df, use_container_width=True)

    # ---------- DOWNLOAD ----------
    st.subheader("📥 Download Data")

    excel_buffer = io.BytesIO()
    filtered_df.to_excel(excel_buffer, index=False)

    file_name = "all_data.xlsx" if (
        area_filter == "All" and category_filter == "All" and not search_owner
    ) else "filtered_data.xlsx"

    st.download_button(
        label="Download Excel",
        data=excel_buffer.getvalue(),
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------- EDIT / DELETE ----------
elif menu == "Edit / Delete":
    st.subheader("Edit or Delete Lead")

    if df.empty:
        st.info("No leads available.")
    else:
        selected = st.selectbox(
            "Select Lead",
            df.itertuples(),
            format_func=lambda x: f"{x.Owner_Builder_name} ({x.Area})"
        )

        row_number = selected.Index + 2

        new_price = st.text_input("Price", value=selected.Price)
        new_comments = st.text_area("Comments", value=selected.Comments)

        if st.button("Update"):
            update_item(row_number, new_price, new_comments)
            st.session_state.df = fetch_inventory()
            st.success("✅ Updated successfully")
            st.rerun()

        if st.button("Delete"):
            delete_item(row_number)
            st.session_state.df = fetch_inventory()
            st.warning("❌ Deleted")
            st.rerun()
