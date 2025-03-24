from flask import Flask, render_template, request, redirect, url_for, session
import json
import random
import functions
import definition
from definition import get_definition

app = Flask(__name__)
app.secret_key = 'votre_clé_secrète_ici'

secret_word = None
word_set = None
to_display = None
tries = None
blanks = None

# Chargement des questions depuis le fichier JSON
def load_questions():
    with open('QuizData.json', 'r', encoding='utf-8') as file:
        return json.load(file)


CATEGORIES = [
    "Histoire",
    "Géographie",
    "Science",
    "Divertissement",
    "Art et Littérature",
    "Sport et Loisirs"
]


def init_game_state():
    # Choix aléatoire d'un mot depuis une liste prédéfinie
    word_set = ["PYTHON", "JAVASCRIPT", "HANGMAN", "PROGRAMMING", "DEVELOPER",
                "FLASK", "INTERNET", "ORDINATEUR", "CLAVIER", "LOGICIEL"]

    # Forcer un nouveau mot différent si possible
    old_word = session.get('secret_word', '')
    new_word = old_word

    # S'assurer que le nouveau mot est différent de l'ancien (si la liste contient assez de mots)
    if len(word_set) > 1 and old_word in word_set:
        while new_word == old_word and len(word_set) > 1:
            new_word = random.choice(word_set)
    else:
        new_word = random.choice(word_set)

    # Mettre à jour la session avec le nouveau mot
    session['secret_word'] = new_word

    # Réinitialiser complètement l'affichage pour le nouveau mot
    session['to_display'] = ["_" for _ in new_word]

    # Réinitialiser les autres variables
    session['tries'] = 6
    session['used_letters'] = []
    session['blanks'] = len(new_word)

    # Debug: imprimer le mot secret dans la console (à supprimer en production)
    print(f"Nouveau mot: {new_word}")



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
        if 'restart' in request.form:
            session['game_state'] = init_game_state()
            return redirect(url_for('index'))

        elif 'start' in request.form:
            game_state['partie_commencee'] = True
            session['game_state'] = game_state
            return redirect(url_for('question'))

    return render_template('TrivialPursuit.html',
                           nb_joueurs=game_state['nb_joueurs'],
                           scores=game_state['scores'],
                           joueur_actuel=game_state['joueur_actuel'],
                           categories=CATEGORIES,
                           partie_commencee=game_state['partie_commencee'])


@app.route('/question', methods=['GET'])
def question():
    game_state = session['game_state']

    if not game_state['partie_commencee']:
        return redirect(url_for('index'))

    # Sélectionner une question aléatoire non posée
    questions_disponibles = [q for q in game_state['questions']
                             if q['id'] not in game_state['questions_posees']]

    if not questions_disponibles:
        game_state['questions_posees'] = []
        questions_disponibles = game_state['questions']

    question = random.choice(questions_disponibles)
    game_state['question_actuelle'] = question
    game_state['questions_posees'].append(question['id'])
    session['game_state'] = game_state

    # Mélanger les réponses
    reponses = [question['correct_answer']] + question['incorrect_answers']
    random.shuffle(reponses)

    return render_template('TrivialPursuit.html',
                           nb_joueurs=game_state['nb_joueurs'],
                           scores=game_state['scores'],
                           joueur_actuel=game_state['joueur_actuel'],
                           categories=CATEGORIES,
                           question={
                               'category': question['category'],
                               'question': question['question'],
                               'reponses': reponses
                           })


@app.route('/check_answer', methods=['POST'])
def check_answer():
    game_state = session['game_state']
    reponse_joueur = request.form.get('reponse')

    if game_state['question_actuelle']:
        if reponse_joueur == game_state['question_actuelle']['correct_answer']:
            game_state['scores'][game_state['joueur_actuel'] - 1] += 1

        game_state['joueur_actuel'] = (game_state['joueur_actuel'] % game_state['nb_joueurs']) + 1
        session['game_state'] = game_state

    return redirect(url_for('question'))


@app.template_filter('zip')
def zip_filter(a, b):
    return zip(a, b)


@app.context_processor
def utility_processor():
    def get_color_for_category(category):
        category_colors = {
            "Histoire": "#e63946",
            "Géographie": "#457b9d",
            "Science": "#2a9d8f",
            "Divertissement": "#f4a261",
            "Art et Littérature": "#9d4edd",
            "Sport et Loisirs": "#e5989b"
        }
        return category_colors.get(category, "#000000")

    return dict(get_color_for_category=get_color_for_category)


@app.route('/categories')
def categories():
    game_state = session['game_state']
    return render_template('categories.html',
                           categories=CATEGORIES,
                           scores=game_state['scores'],
                           nb_joueurs=game_state['nb_joueurs'])

#HangMan Part
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
    # S'assurer que toutes les variables de jeu sont initialisées
    if 'secret_word' not in session or 'to_display' not in session or 'tries' not in session:
        init_game_state()

    return render_template('game.html',
                           word=session['to_display'],
                           tries=session['tries'],
                           score=session.get('score', 0))

@app.route('/new_game')
def new_game():
    # Forcer la réinitialisation du jeu
    init_game_state()
    return redirect(url_for('game'))


@app.route('/add_char/<char>')
def add_char(char):
    # Vérifier que le jeu est bien initialisé
    if 'secret_word' not in session or 'to_display' not in session or 'tries' not in session:
        # Si le jeu n'est pas initialisé correctement, redémarrer une partie
        init_game_state()
        return redirect(url_for('game'))

    # Convertir le caractère en majuscule pour la cohérence
    char = char.upper()

    # Ignorer si c'est une lettre déjà utilisée
    if 'used_letters' not in session:
        session['used_letters'] = []

    if char in session.get('used_letters', []):
        # La lettre a déjà été jouée, ne rien faire
        return redirect(url_for('game'))

    # Ajouter la lettre aux lettres utilisées
    session_used_letters = list(session.get('used_letters', []))
    session_used_letters.append(char)
    session['used_letters'] = session_used_letters

    # Créer des copies modifiables des variables de session
    secret_word = session.get('secret_word', '')
    to_display = list(session.get('to_display', []))
    blanks = session.get('blanks', 0)
    tries = session.get('tries', 6)

    # Vérifier si la lettre est dans le mot secret
    if char in secret_word:
        # Mettre à jour l'affichage
        for i in range(len(secret_word)):
            if secret_word[i] == char:
                to_display[i] = char
                blanks -= 1

        # Mettre à jour les variables de session
        session['to_display'] = to_display
        session['blanks'] = blanks

        # Vérifier si le joueur a gagné
        if "_" not in to_display or blanks <= 0:
            return redirect(url_for('game_won_landing'))
    else:
        # Réduire le nombre d'essais disponibles
        tries -= 1
        session['tries'] = tries

        # Vérifier si le joueur a perdu
        if tries <= 0:
            return redirect(url_for('game_lost_landing'))

    return redirect(url_for('game'))


@app.route('/game_lost')
def game_lost_landing():
    return render_template('game_lost.html')


@app.route('/game_won')
def game_won_landing():
    # Incrémenter le score quand le joueur gagne
    if 'score' in session:
        session['score'] += 1
    else:
        session['score'] = 1

    return render_template('game_won.html')



#Don't Forget the lyrics
# Liste de chansons populaires avec leurs paroles manquantes
SONGS = [
    {
        "artist": "Queen",
        "title": "Bohemian Rhapsody",
        "lyrics": "Is this the real life? Is this just fantasy? Caught in a landslide, No escape from...",
        "answer": "reality",
    },
    {
        "artist": "Michael Jackson",
        "title": "Billie Jean",
        "lyrics": "Billie Jean is not my lover. She's just a girl who claims that I am the one. But the kid is not my...",
        "answer": "son",
    },
    {
        "artist": "The Beatles",
        "title": "Hey Jude",
        "lyrics": "Hey Jude, don't make it bad. Take a sad song and make it...",
        "answer": "better",
    },
    {
        "artist": "Adele",
        "title": "Rolling in the Deep",
        "lyrics": "There's a fire starting in my heart, reaching a fever pitch and it's bringing me out the...",
        "answer": "dark",
    },
    {
        "artist": "Rick Astley",
        "title": "Never Gonna Give You Up",
        "lyrics": "Never gonna give you up, never gonna let you down, never gonna run around and...",
        "answer": "desert you",
    },
]


@app.route('/dftl')
def dftl():
    """Page d'accueil du jeu Don't Forget The Lyrics"""
    # Réinitialiser le score stocké en session
    if 'dftl_score' not in session:
        session['dftl_score'] = 0

    return render_template('dftl.html')


@app.route('/dftl/play')
def dftl_play():
    """Page de jeu DFTL"""
    # Sélectionner une chanson aléatoire
    song = random.choice(SONGS)
    session['current_song'] = song

    return render_template('dftl_play.html', song=song)


@app.route('/dftl/check', methods=['POST'])
def dftl_check():
    """Vérifier la réponse du joueur"""
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

#END HangMan Part

if __name__ == '__main__':
    app.run(debug=True)
