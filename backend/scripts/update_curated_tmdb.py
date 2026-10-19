import re

poster_mapping = {
    # Series
    'Breaking Bad': ('1396', 'https://image.tmdb.org/t/p/w500/anFx9aTOOYqgS3v7x3R84Kz67ly.jpg'),
    'Game of Thrones': ('1399', 'https://image.tmdb.org/t/p/w500/1XS1oqL89opfnbLl8WnZY1O1uJx.jpg'),
    'Dark': ('2883', 'https://image.tmdb.org/t/p/w500/eRtnI7qTJIiPUmlY3J8TTM3jlT7.jpg'),
    'Chernobyl': ('87108', 'https://image.tmdb.org/t/p/w500/hlLXt2tOPT6RRnjiUmoxyG1LTFi.jpg'),
    'Band of Brothers': ('4613', 'https://image.tmdb.org/t/p/w500/eLdcio9HBKzsdIJGeD80oObDfkr.jpg'),
    'Vikings': ('44217', 'https://image.tmdb.org/t/p/w500/bQLrHIRNEkE3PdIWQrZHynQZazu.jpg'),
    'Peaky Blinders': ('60574', 'https://image.tmdb.org/t/p/w500/vUUqzWa2LnHIVqkaKVlVGkVcZIW.jpg'),
    'Severance': ('95396', 'https://image.tmdb.org/t/p/w500/pPHpeI2X1qEd1CS1SeyrdhZ4qnT.jpg'),
    'Better Call Saul': ('60059', 'https://image.tmdb.org/t/p/w500/fC2HDm5t0kHl7mTm7jxMR31b7by.jpg'),
    'Mr. Robot': ('62560', 'https://image.tmdb.org/t/p/w500/kv1nRqgebSsREnd7vdC2pSGjpLo.jpg'),
    'True Detective': ('46648', 'https://image.tmdb.org/t/p/w500/cuV2O5ZyDLHSOWzg3nLVljp1ubw.jpg'),
    'Stranger Things': ('66732', 'https://image.tmdb.org/t/p/w500/uOOtwVbSr4QDjAGIifLDwpb2Pdl.jpg'),
    'Black Mirror': ('42009', 'https://image.tmdb.org/t/p/w500/seN6rRfN0I6n8iDXjlSMk1QjNcq.jpg'),

    # Movies
    'Inception': ('27205', 'https://image.tmdb.org/t/p/w500/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg'),
    'Interstellar': ('157336', 'https://image.tmdb.org/t/p/w500/yQvGrMoipbRoddT0ZR8tPoR7NfX.jpg'),
    'The Dark Knight': ('155', 'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg'),
    'Fight Club': ('550', 'https://image.tmdb.org/t/p/w500/jSziioSwPVrOy9Yow3XhWIBDjq1.jpg'),
    'Pulp Fiction': ('680', 'https://image.tmdb.org/t/p/w500/vQWk5YBFWF4bZaofAbv0tShwBvQ.jpg'),
    'The Matrix': ('603', 'https://image.tmdb.org/t/p/w500/dXNAPwY7VrqMAo51EKhhCJfaGb5.jpg'),
    'Parasite': ('496243', 'https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg'),
    'Dune': ('438631', 'https://image.tmdb.org/t/p/w500/v1tRXZ4JtD2Iv6fjkPvT4GiwslV.jpg'),
    'Dune: Part Two': ('693134', 'https://image.tmdb.org/t/p/w500/6izwz7rsy95ARzTR3poZ8H6c5pp.jpg'),
    'Whiplash': ('244786', 'https://image.tmdb.org/t/p/w500/7fn624j5lj3xTme2SgiLCeuedmO.jpg'),
    'Se7en': ('807', 'https://image.tmdb.org/t/p/w500/191nKfP0ehp3uIvWqgPbFmI4lv9.jpg'),
    'Gladiator': ('98', 'https://image.tmdb.org/t/p/w500/aDb548BOkFfI4nFm0kx8A3Ezh7H.jpg'),
    "Schindler's List": ('424', 'https://image.tmdb.org/t/p/w500/sF1U4EUQS8YHUYjNl3pMGNIQyr0.jpg'),
    'The Pianist': ('423', 'https://image.tmdb.org/t/p/w500/2hFvxCCWrTmCYwfy7yum0GKRi3Y.jpg'),
    '1917': ('530915', 'https://image.tmdb.org/t/p/w500/iZf0KyrE25z1sage4SYFLCCrMi9.jpg'),
    'Saving Private Ryan': ('857', 'https://image.tmdb.org/t/p/w500/uqx37cS8cpHg8U35f9U5IBlrCV3.jpg'),
    'Braveheart': ('197', 'https://image.tmdb.org/t/p/w500/or1gBugydmjToAEq7OZY0owwFk.jpg'),
    'The Prestige': ('1124', 'https://image.tmdb.org/t/p/w500/Ag2B2KHKQPukjH7WutmgnnSNurZ.jpg'),
    'Memento': ('77', 'https://image.tmdb.org/t/p/w500/nzlv62aC0octS5AklAiWpXLX9Z0.jpg'),
    'The Shawshank Redemption': ('278', 'https://image.tmdb.org/t/p/w500/9cqNxx0GxF0bflZmeSMuL5tnGzr.jpg'),
    'The Godfather': ('238', 'https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg'),
    'Blade Runner 2049': ('335984', 'https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg'),
    'Arrival': ('329865', 'https://image.tmdb.org/t/p/w500/pEzNVQfdzYDzVK0XqxERIw2x2se.jpg'),
    'Shutter Island': ('11324', 'https://image.tmdb.org/t/p/w500/nrmXQ0zcZUL8jFLrakWc90IR8z9.jpg'),
    'No Country for Old Men': ('6977', 'https://image.tmdb.org/t/p/w500/6d5XOczc226jECq0LIX0siKtgHR.jpg'),
    'Oldboy': ('87516', 'https://image.tmdb.org/t/p/w500/iX93YdBrZA1EpGbphmjf4ARj1Za.jpg'),
    'Eternal Sunshine of the Spotless Mind': ('38', 'https://image.tmdb.org/t/p/w500/5MwkWH9tYHv3mV9OdYTMR5qreIz.jpg'),
    'The Silence of the Lambs': ('274', 'https://image.tmdb.org/t/p/w500/uS9m8OBk1A8eM9I042bx8XXpqAq.jpg'),
    'Mad Max: Fury Road': ('76341', 'https://image.tmdb.org/t/p/w500/ulcAi4dKpAjHwYGS08vNyx9H6I9.jpg'),
    'Prisoners': ('146233', 'https://image.tmdb.org/t/p/w500/uhviyknTT5cEQXbn6vWIqfM4vGm.jpg'),
    'Gone Girl': ('210577', 'https://image.tmdb.org/t/p/w500/ts996lKsxvjkO2yiYG0ht4qAicO.jpg'),
    'Joker': ('475557', 'https://image.tmdb.org/t/p/w500/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg'),
    'Oppenheimer': ('872585', 'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg'),
    'Spider-Man: Across the Spider-Verse': ('569094', 'https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg'),
    'Inglourious Basterds': ('16869', 'https://image.tmdb.org/t/p/w500/aupnPtagH9JVBuMrGEanf4iqXEQ.jpg'),
    'Requiem for a Dream': ('641', 'https://image.tmdb.org/t/p/w500/9BTwsLaMVHOGFlmsSlx5QYCaXb.jpg'),
    'Donnie Darko': ('141', 'https://image.tmdb.org/t/p/w500/j2AtZFsflxiluaNtajMTI0Avm8C.jpg'),
}

file_path = "app/services/external/tmdb_client.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

updated = content
for title, (t_id, poster) in poster_mapping.items():
    # Replace external_id and poster_url in dict block for this title
    pattern = rf'({{\s*"external_id":\s*")[^"]*("\s*,\s*"title":\s*"{re.escape(title)}".*?"poster_url":\s*")[^"]*(")'
    def repl(m):
        return f'{m.group(1)}{t_id}{m.group(2)}{poster}{m.group(3)}'
    new_updated, count = re.subn(pattern, repl, updated, flags=re.DOTALL)
    if count > 0:
        updated = new_updated
        print(f"Updated {title} -> {t_id}")
    else:
        print(f"FAILED to match {title}")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(updated)
print("Finished updating tmdb_client.py!")
