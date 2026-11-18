import streamlit as st
# http://127.0.0.1:8000

import requests

# Basic POST with JSON
url = "http://127.0.0.1:8000/penguins/"




body_mass = st.number_input("Body mass: ", key = 1)
bill_length_mm = st.number_input("bill_length_mm: ", key = 2)
bill_depth_mm = st.number_input("bill_depth_mm: ", key = 3)
flipper_length_mm = st.number_input("flipper_length_mm: ", key = 4)
sex = st.selectbox("Sex",options=["Male", "Female", "Unkown"])

submited = st.button("Predict Species")

if submited:
    data = {
            "bill_length_mm": bill_length_mm,
            "bill_depth_mm": bill_depth_mm,
            "flipper_length_mm": flipper_length_mm,
            "body_mass_g": body_mass,
            "sex": sex 
        }
    response = requests.post(url, json=data)
    st.write(response.json())