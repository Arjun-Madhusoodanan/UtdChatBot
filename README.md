# SETUP GUIDE (NO ICONS / MARKDOWN)

1. Clone the repository (or navigate to your project folder):

   git clone https://github.com/your-username/chatbot_utd.git
   cd chatbot_utd

2. Create and activate a virtual environment:

   python -m venv utd_bot_env
   # On Windows:
   utd_bot_env\Scripts\activate
   # On macOS/Linux:
   source utd_bot_env/bin/activate

3. Install dependencies:

   pip install -r requirements.txt

   # If you don't have a requirements.txt, install manually:
   pip install openai langchain langchain-openai langchain-community faiss-cpu pandas python-dotenv

4. Set your OpenAI API key:

   # Option 1 - Set it as an environment variable
   set OPENAI_API_KEY=sk-...         (on Windows)
   export OPENAI_API_KEY=sk-...      (on macOS/Linux)

   # Option 2 - Create a .env file with this line:
   OPENAI_API_KEY=sk-...

5. Run the chatbot:

   python main.py

6. Ask questions in the terminal.
   Type 'exit' or 'quit' to stop the bot.
