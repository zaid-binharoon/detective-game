import streamlit as st
import random
import json
from google import genai
from google.genai import types

# --- PAGE SETUP ---
st.set_page_config(page_title="AI Murder Mystery", page_icon="🕵️‍♂️", layout="wide")

# --- SECRETS SETUP ---
# Securely load the API key from Streamlit Secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ GEMINI_API_KEY not found in Streamlit Secrets!")
    st.info("If deploying to Streamlit Cloud, add it to your app's App Settings > Secrets.")
    st.info("If running locally, create a .streamlit/secrets.toml file.")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "message" not in st.session_state:
    st.session_state.message = ""

def notify(msg):
    st.session_state.message = msg

# --- AI GENERATION FUNCTION ---
def fetch_new_case():
    try:
        client = genai.Client(api_key=API_KEY)
        
        prompt = """
        You are a mystery writer. Generate a murder mystery scenario. 
        Return ONLY a raw JSON object (no markdown formatting, no comments).
        Follow this exact JSON structure:
        {
          "victim": "Name of the victim",
          "suspects": [
            {
              "name": "First Name",
              "role": "Their job or relation",
              "alibi": "A 1-sentence alibi of where they were.",
              "clue": "A 1-sentence physical clue found near the body pointing to them.",
              "contradiction_clue": "A 1-sentence physical clue found elsewhere that proves their alibi is a lie.",
              "secret": "A 1-sentence confession of what they were ACTUALLY doing (a secret, but NOT the murder)."
            }
          ]
        }
        Generate exactly 3 suspects in the suspects array.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.8 
            )
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"API Error: Make sure your API key is valid. Details: {e}")
        return None

def init_game():
    mystery_data = fetch_new_case()
    if mystery_data:
        st.session_state.victim = mystery_data["victim"]
        st.session_state.suspects = mystery_data["suspects"]
        st.session_state.score = 0
        st.session_state.notebook = []
        st.session_state.exposed_suspects = []
        st.session_state.actual_murderer = random.choice(st.session_state.suspects)["name"]
        
        clues = [suspect["contradiction_clue"] for suspect in st.session_state.suspects]
        random.shuffle(clues)
        st.session_state.manor_clues = clues
        
        st.session_state.game_over = False
        st.session_state.message = "New case file received from the Chief!"
        st.session_state.game_started = True

# --- SIDEBAR UI ---
with st.sidebar:
    st.header("🕵️‍♂️ Detective's Dashboard")
    
    if not st.session_state.game_started:
        if st.button("🚨 Start New Case", type="primary", use_container_width=True):
            with st.spinner("Connecting to police database (Generating story)..."):
                init_game()
                st.rerun()
    else:
        st.metric(label="Detective Points ⭐", value=st.session_state.score)
        st.divider()
        
        st.subheader("📓 Clue Notebook")
        if not st.session_state.notebook:
            st.caption("Your notebook is empty. Search the room or question suspects!")
        else:
            for i, clue in enumerate(st.session_state.notebook):
                st.info(f"{i + 1}. {clue}")
                
        st.divider()
        if st.button("🔄 Abandon Case (Restart)", use_container_width=True):
            st.session_state.game_started = False
            st.rerun()

# --- MAIN AREA UI ---
st.title("The Manor Murder Mystery 🔎")

if not st.session_state.game_started:
    st.info("👈 Click 'Start New Case' in the sidebar to generate a completely unique mystery powered by AI!")
    st.stop()

st.markdown(f"**Tragedy strikes! {st.session_state.victim} has been murdered.**")

if st.session_state.message:
    st.success(st.session_state.message)

if st.session_state.game_over:
    st.error(f"**CASE CLOSED.** Final Score: {st.session_state.score}")
    st.stop() 

tab_search, tab_suspects, tab_accuse = st.tabs(["🚪 Search Scene", "👥 Suspect Cards", "⚖️ Accuse"])

# --- TAB 1: Search Scene ---
with tab_search:
    st.subheader("Examine the Crime Scene")
    st.write("Search the area for hidden clues that contradict the suspects' alibis.")
    
    if st.button("Search for Clues 🔎"):
        if len(st.session_state.manor_clues) > 0:
            found_clue = st.session_state.manor_clues.pop(0)
            st.session_state.notebook.append(found_clue)
            st.session_state.score += 10
            notify(f"NEW CLUE FOUND: {found_clue} (+10 Points)")
            st.rerun()
        else:
            notify("You have thoroughly searched the area. Nothing else to find.")
            st.rerun()

# --- TAB 2: Suspect Cards ---
with tab_suspects:
    st.subheader("Interrogate Suspects & Expose Lies")
    cols = st.columns(3)
    
    for i, suspect in enumerate(st.session_state.suspects):
        name = suspect['name']
        with cols[i]:
            with st.container(border=True):
                st.subheader(f"👤 {name}")
                st.caption(f"Role: {suspect['role']}")
                
                if st.button(f"Interrogate", key=f"int_{name}", use_container_width=True):
                    suspect_clue = suspect['clue']
                    if suspect_clue not in st.session_state.notebook:
                        st.session_state.notebook.append(suspect_clue)
                        st.session_state.score += 10
                        notify(f"'{suspect['alibi']}' — Note taken! (+10 Points)")
                    else:
                        notify(f"'{suspect['alibi']}' — You already wrote this down.")
                    st.rerun()
                
                st.divider()
                
                if name in st.session_state.exposed_suspects:
                    st.success(f"Secret: '{suspect['secret']}'")
                else:
                    st.write("Press with Evidence:")
                    options = ["Select a clue..."] + st.session_state.notebook
                    selected_clue = st.selectbox("Clues", options, label_visibility="collapsed", key=f"sel_{name}")
                    
                    if st.button(f"Present Clue", key=f"btn_{name}", use_container_width=True):
                        if selected_clue == "Select a clue...":
                            notify("Select a clue from your notebook first!")
                        elif selected_clue == suspect["contradiction_clue"]:
                            st.session_state.exposed_suspects.append(name)
                            st.session_state.score += 50
                            notify(f"LIE EXPOSED! {name}: '{suspect['secret']}' (+50 Points)")
                        else:
                            st.session_state.score -= 5
                            notify(f"{name} looks confused. 'That has nothing to do with me.' (-5 Points)")
                        st.rerun()

# --- TAB 3: Make Accusation ---
with tab_accuse:
    st.subheader("Ready to close the case?")
    st.warning("Warning: Making an accusation will end the game.")
    
    suspect_names = [s["name"] for s in st.session_state.suspects]
    accused_name = st.radio("Who is the murderer?", suspect_names, index=None)
    
    if st.button("Arrest Suspect 🚨", type="primary"):
        if accused_name:
            if accused_name == st.session_state.actual_murderer:
                st.session_state.score += 100
                notify(f"🎉 CORRECT! {accused_name} confesses to the crime! (+100 Points)")
            else:
                notify(f"❌ WRONG! {accused_name} is innocent. The real murderer was {st.session_state.actual_murderer}.")
            
            st.session_state.game_over = True
            st.rerun()
        else:
            notify("You must select a suspect to arrest.")
            st.rerun()
