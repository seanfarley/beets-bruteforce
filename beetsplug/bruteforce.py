import sys
import traceback

import requests
import wikipedia

from bs4 import BeautifulSoup
from beets import config, ui
from beets.autotag import mb
from beets.autotag.hooks import AlbumMatch, string_dist
from beets.autotag.match import distance
from beets.plugins import BeetsPlugin


class BruteforcePlugin(BeetsPlugin):
    def __init__(self):
        super(BruteforcePlugin, self).__init__()
        self.register_listener("before_choose_candidate", self.search_wikipedia)

    def search_wikipedia(self, session, task):
        wikipedia.set_lang("en")  # Set language to English

        # Fetch the album name, artist, and title from the first item
        if task.items:
            artist_name = task.items[0].artist
            title_name = task.items[0].title
        else:
            ui.print_("No items in this task.")
            return

        try:
            # search wikipedia for the artist + title (but no album) and get
            # the first result
            search_results = wikipedia.search(f"{artist_name} {title_name}")

            # sometimes the album has the same name as the song, so as a
            # (perhaps bad) hueristic we remove search results that end in
            # '_(album)'
            search_results = [
                r for r in search_results if not r.lower().endswith(" (album)")
            ]

            # no need to test search_results being empty since we're in a giant
            # try / catch
            page_title = search_results[0]

            # build url
            url = page_title.replace(" ", "_")
            response = requests.get(f"https://en.wikipedia.org/wiki/{url}")
            soup = BeautifulSoup(response.text, "html.parser")
            album = soup.select_one(".infobox .infobox-header i a")

            url = f'https://en.wikipedia.org/{album["href"]}'
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            rg_id = soup.select_one(".authority-control td .uid a")["href"]

            response = requests.get(rg_id)
            soup = BeautifulSoup(response.text, "html.parser")

            country = None
            try:
                country = config["match"]["preferred"]["countries"]
                country = country.get(list)[0]
            except Exception:
                country = "US"

            # # TODO change into setting
            ban_formats = []  # ["cassette", "vinyl"]

            # luckily for us, releases are sorted by date so we just need to
            # get the ones for our prefered country
            # HACK ugly code just to skip unwanted formats
            release_tr = None
            for tr in soup.select(".tbl tbody tr.odd, .tbl tbody tr.even"):
                if tr.select(f".flag-{country}"):
                    # should be ordered
                    td = tr.select("td")[2].text.lower()
                    is_banned = [b for b in ban_formats if b.lower() in td]

                    if not is_banned:
                        release_tr = tr
                        break

            mb_id = release_tr.select("a")[0]["href"]
            mb_id = mb_id.replace("/release/", "")
            mb_id = mb_id.replace("/cover-art", "")

            album_info = mb.album_for_id(mb_id)

            # compute the closest matching title from our given title
            best_match = min(
                album_info.tracks,
                key=lambda track: string_dist(track.title, title_name),
            )

            # this mapping helps instruct beets which is the actual track
            # to use
            mapping = dict(zip(task.items, [best_match]))

            dist = distance(task.items, album_info, mapping)

            album_candidate = AlbumMatch(dist, album_info, mapping, {}, {})
            task.candidates.insert(0, album_candidate)

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback_details = traceback.extract_tb(exc_traceback)
            first_line_traceback = traceback_details[0]
            line_number = first_line_traceback.lineno
            text = first_line_traceback.line

            ui.print_("---------")
            ui.print_(f"Bruteforce wikipedia search failed: {e}")
            ui.print_(
                f"Bruteforce wikipedia failed line: " f"{line_number}: {text}"
            )
            ui.print_("---------")
