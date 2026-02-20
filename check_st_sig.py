import inspect
import streamlit as st

sig = inspect.signature(st.text_input)
print(sig)
