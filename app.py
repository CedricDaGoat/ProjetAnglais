from flask import Flask, render_template, request, redirect, url_for, session
import json
import random
import functions
import definition
from definition import get_definition
from words import word_set
from songs import SONGS

app = Flask(__name__)
app.secret_key = 'votre_clé_secrète_ici'

CATEGORIES = [
    "History",
    "Geography",
    "Science",
    "Entertainment",
    "Arts and litterature",
    "Sports"
]

def load_questions():
    with open('QuizData.json', 'r', encoding='utf-8') as file:
        return json.load(file)


def init_game_state(nbrjoueur=1):
    # Choix aléatoire du mot pour Hangman (réutilisé ailleurs)

    old_word = session.get('secret_word', '')
    new_word = old_word

    if len(word_set) > 1 and old_word in word_set:
        while new_word == old_word:
            new_word = random.choice(word_set)
    else:
        new_word = random.choice(word_set)

    session['secret_word'] = new_word
    session['to_display'] = ["_" for _ in new_word]
    session['tries'] = 9
    session['used_letters'] = []
    session['blanks'] = len(new_word)

    # Initialisation de l'état de jeu
    game_state = {
        'nb_joueurs': nbrjoueur,
        'scores': [0],  # un seul joueur
        'joueur_actuel': 1,
        'questions': load_questions(),
        'questions_posees': [],
        'question_actuelle': None,
        'partie_commencee': False
    }

    # Initialiser le score maximum si nécessaire
    if 'max_score' not in session:
        session['max_score'] = 0

    session['game_state'] = game_state
    return game_state


@app.route('/definition', methods=['GET', 'POST'])
def definition():
    definitions = []
    mot = None
    if request.method == 'POST':
        mot = request.form.get('mot', '')
        if mot:
            definitions = get_definition(mot)
    return render_template('definition.html', definitions=definitions, mot=mot)


@app.route('/trivial', methods=['GET', 'POST'])
def index():
    if 'game_state' not in session:
        session['game_state'] = init_game_state()

    game_state = session['game_state']

    if request.method == 'POST':
        # Bouton Nouvelle Partie
        if 'restart' in request.form:
            session['game_state'] = init_game_state(1)
            return redirect(url_for('index'))

        # Bouton Commencer la partie
        elif 'start' in request.form:
            game_state = init_game_state()
            game_state['partie_commencee'] = True
            session['game_state'] = game_state
            return redirect(url_for('question'))

    return render_template('TrivialPursuit.html',
                           nb_joueurs=game_state['nb_joueurs'],
                           scores=game_state['scores'],
                           joueur_actuel=game_state['joueur_actuel'],
                           categories=CATEGORIES,
                           partie_commencee=game_state['partie_commencee'],
                           max_score=session.get('max_score', 0))


@app.route('/question', methods=['GET'])
def question():
    game_state = session['game_state']

    if not game_state['partie_commencee']:
        return redirect(url_for('index'))

    questions_disponibles = [q for q in game_state['questions']
                             if q['id'] not in game_state['questions_posees']]

    if not questions_disponibles:
        game_state['questions_posees'] = []
        questions_disponibles = game_state['questions']

    question = random.choice(questions_disponibles)
    game_state['question_actuelle'] = question
    game_state['questions_posees'].append(question['id'])
    session['game_state'] = game_state

    reponses = [question['correct_answer']] + question['incorrect_answers']
    random.shuffle(reponses)

    return render_template('TrivialPursuit.html',
                           nb_joueurs=game_state['nb_joueurs'],
                           scores=game_state['scores'],
                           joueur_actuel=game_state['joueur_actuel'],
                           categories=CATEGORIES,
                           partie_commencee=game_state['partie_commencee'],
                           question={
                               'category': question['category'],
                               'question': question['question'],
                               'reponses': reponses
                           },
                           max_score=session.get('max_score', 0))


@app.route('/check_answer', methods=['POST'])
def check_answer():
    game_state = session['game_state']
    reponse_joueur = request.form.get('reponse')

    if game_state['question_actuelle']:
        if reponse_joueur == game_state['question_actuelle']['correct_answer']:
            # Incrémenter le score du joueur
            idx = game_state['joueur_actuel'] - 1
            game_state['scores'][idx] += 1

            # Mettre à jour le score maximum si nécessaire
            nouveau_max = game_state['scores'][idx]
            if nouveau_max > session.get('max_score', 0):
                session['max_score'] = nouveau_max

        session['game_state'] = game_state

    return redirect(url_for('question'))


@app.template_filter('zip')
def zip_filter(a, b):
    return zip(a, b)


@app.context_processor
def utility_processor():
    def get_color_for_category(category):
        category_colors = {
            "History": "#e63946",
            "Geography": "#457b9d",
            "Science": "#2a9d8f",
            "Entertainment": "#f4a261",
            "Arts and litterature": "#9d4edd",
            "Sports": "#e5989b"
        }
        return category_colors.get(category, "#000000")
    return dict(get_color_for_category=get_color_for_category)


@app.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/')
def hello_world():
    return render_template('home.html')

@app.route('/game')
def game():
    if 'secret_word' not in session or 'to_display' not in session or 'tries' not in session:
        init_game_state()

    return render_template('game.html',
                           word=session['to_display'],
                           tries=session['tries'],
                           score=session.get('score', 0))

@app.route('/new_game')
def new_game():
    init_game_state()
    return redirect(url_for('game'))

@app.route('/add_char/<char>')
def add_char(char):
    if 'secret_word' not in session or 'to_display' not in session or 'tries' not in session:
        init_game_state()
        return redirect(url_for('game'))

    char = char.upper()

    if 'used_letters' not in session:
        session['used_letters'] = []

    if char in session.get('used_letters', []):
        return redirect(url_for('game'))

    session_used_letters = list(session.get('used_letters', []))
    session_used_letters.append(char)
    session['used_letters'] = session_used_letters

    secret_word = session.get('secret_word', '')
    to_display = list(session.get('to_display', []))
    blanks = session.get('blanks', 0)
    tries = session.get('tries', 9)

    if char in secret_word:
        for i in range(len(secret_word)):
            if secret_word[i] == char:
                to_display[i] = char
                blanks -= 1

        session['to_display'] = to_display
        session['blanks'] = blanks

        if "_" not in to_display or blanks <= 0:
            return redirect(url_for('game_won_landing'))
    else:
        tries -= 1
        session['tries'] = tries

        if tries <= 0:
            return redirect(url_for('game_lost_landing'))

    return redirect(url_for('game'))

@app.route('/game_lost')
def game_lost_landing():
    return render_template('game_lost.html')

@app.route('/game_won')
def game_won_landing():
    if 'score' in session:
        session['score'] += 1
    else:
        session['score'] = 1

    return render_template('game_won.html')

@app.route('/dftl')
def dftl():
    session['dftl_score'] = 0
    session['dftl_played'] = []  # Réinitialise la liste des chansons jouées
    return render_template('dftl.html')


@app.route('/dftl/play')
def dftl_play():
    if 'dftl_played' not in session:
        session['dftl_played'] = []

    # Filtrer les chansons déjà jouées
    remaining_songs = [song for song in SONGS if song['answer'] not in session['dftl_played']]

    # Si toutes les chansons ont été jouées, on réinitialise ou affiche un message
    if not remaining_songs:
        session['dftl_played'] = []  # Ou rediriger vers un écran de fin
        return render_template('dftl_complete.html')  # À créer

    # Choisir une chanson parmi celles restantes
    song = random.choice(remaining_songs)
    session['current_song'] = song

    # Ajouter à la liste des chansons déjà jouées
    session['dftl_played'].append(song['answer'])

    return render_template('dftl_play.html', song=song)


@app.route('/dftl/check', methods=['POST'])
def dftl_check():
    user_answer = request.form.get('answer', '').strip().lower()
    current_song = session.get('current_song')

    if not current_song:
        return redirect(url_for('dftl'))

    correct = user_answer == current_song['answer'].lower()

    if correct:
        session['dftl_score'] = session.get('dftl_score', 0) + 1
        return render_template('dftl_correct.html',
                               score=session['dftl_score'],
                               song=current_song)
    else:
        return render_template('dftl_wrong.html',
                               score=session['dftl_score'],
                               song=current_song,
                               user_answer=user_answer)


# ... autres routes (Hangman, DFTL, etc.) ...

if __name__ == '__main__':
    app.run(debug=True)