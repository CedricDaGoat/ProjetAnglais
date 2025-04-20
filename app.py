from flask import Flask, render_template, request, redirect, url_for, session
import json
import random
import functions
import definition
from definition import get_definition

app = Flask(__name__)
app.secret_key = 'votre_clé_secrète_ici'

CATEGORIES = [
    "Histoire",
    "Géographie",
    "Science",
    "Divertissement",
    "Art et Littérature",
    "Sport et Loisirs"
]

def load_questions():
    with open('QuizData.json', 'r', encoding='utf-8') as file:
        return json.load(file)


def init_game_state(nbrjoueur=1):
    # Choix aléatoire du mot pour Hangman (réutilisé ailleurs)
    word_set = ["PYTHON", "JAVASCRIPT", "HANGMAN", "PROGRAMMING", "DEVELOPER",
                "FLASK", "INTERNET", "ORDINATEUR", "CLAVIER", "LOGICIEL"]

    old_word = session.get('secret_word', '')
    new_word = old_word

    if len(word_set) > 1 and old_word in word_set:
        while new_word == old_word:
            new_word = random.choice(word_set)
    else:
        new_word = random.choice(word_set)

    session['secret_word'] = new_word
    session['to_display'] = ["_" for _ in new_word]
    session['tries'] = 6
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
        'partie_commencee': False,
        'question_counter': 1
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
    
    # Initialiser le compteur de questions si ce n'est pas déjà fait
    if 'question_counter' not in session:
        session['question_counter'] = 1  # Commencer à 1

    if request.method == 'POST':
        # Bouton Nouvelle Partie
        if 'restart' in request.form:
            session['game_state'] = init_game_state(1)
            session['question_counter'] = 1  # Réinitialiser le compteur de questions
            return redirect(url_for('index'))

        # Bouton Commencer la partie
        elif 'start' in request.form:
            game_state = init_game_state()
            game_state['partie_commencee'] = True
            session['game_state'] = game_state
            session['question_counter'] = 1  # Réinitialiser le compteur de questions
            return redirect(url_for('question'))

    return render_template('TrivialPursuit.html',
                           nb_joueurs=game_state['nb_joueurs'],
                           scores=game_state['scores'],
                           joueur_actuel=game_state['joueur_actuel'],
                           categories=CATEGORIES,
                           partie_commencee=game_state['partie_commencee'],
                           max_score=session.get('max_score', 0),
                           question_counter=session['question_counter'])



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
                           max_score=session.get('max_score', 0),
                           question_counter=session['question_counter'])


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
        session['question_counter'] += 1
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


@app.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/')
def hello_world():
    return render_template('home.html')

# ... autres routes (Hangman, DFTL, etc.) ...

if __name__ == '__main__':
    app.run(debug=True)