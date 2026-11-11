import sqlite3

def init_db():
    conn = sqlite3.connect('spy_game.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            wins INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_player(user_id, username):
    conn = sqlite3.connect('spy_game.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO players (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def update_stats(user_id, won=False):
    conn = sqlite3.connect('spy_game.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE players SET games_played = games_played + 1 WHERE user_id = ?', (user_id,))
    if won:
        cursor.execute('UPDATE players SET wins = wins + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_top_players():
    conn = sqlite3.connect('spy_game.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, wins, games_played FROM players ORDER BY wins DESC LIMIT 5')
    top = cursor.fetchall()
    conn.close()
    return top
