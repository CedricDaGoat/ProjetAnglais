import requests


def get_definition(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and "meanings" in data[0]:
            definitions = []
            for meaning in data[0]["meanings"]:
                for definition in meaning["definitions"]:
                    definitions.append(definition["definition"])
            return definitions
        else:
            return ["Definition not found."]
    else:
        return [f"Error {response.status_code}: Unable to fetch definition."]

"""
# Exemple d'utilisation
word = input("Enter an English word: ")
definitions = get_definition(word)

print(f"\nDefinitions of '{word}':")
for i, definition in enumerate(definitions, 1):
    print(f"{i}. {definition}")
"""