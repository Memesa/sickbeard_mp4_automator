import os
import sys
import requests
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import tempfile
import time
import logging
# from tmdb_api import tmdb
import tmdbsimple as tmdb 
from mutagen.mp4 import MP4, MP4Cover
from extensions import valid_tagging_extensions, valid_poster_extensions, tmdb_api_key


def urlretrieve(url, fn):
    with open(fn, 'wb') as f:
        f.write(requests.get(url, allow_redirects=True, timeout=30).content)
    return (fn, f)


class tmdb_mp4:
    def __init__(self, imdbid, tmdbid=False, original=None, language='en', logger=None):

        if logger:
            self.log = logger
        else:
            self.log = logging.getLogger(__name__)

        if tmdbid:
            self.log.debug("TMDB ID: %s." % tmdbid)
        else:
            self.log.debug("IMDB ID: %s." % imdbid)

        if tmdbid is False and imdbid.startswith('tt') is not True:
            imdbid = 'tt' + imdbid
            self.log.debug("Correcting imdbid to %s." % imdbid)

        self.imdbid = imdbid

        self.original = original
        language = self.checkLanguage(language)

        for i in range(3):
            try:
                tmdb.API_KEY = tmdb_api_key
                query = tmdb.Movies(imdbid)
                self.movie = query.info(language=language)
                self.credit = query.credits()

                self.HD = None

                self.title = self.movie['title']
                self.genre = self.movie['genres']

                self.shortdescription = self.movie['tagline']
                self.description = self.movie['overview']

                self.date = self.movie['release_date']

                # Generate XML tags for Actors/Writers/Directors/Producers
                self.xml = self.xmlTags()
                break
            except Exception as e:
                self.log.exception("Failed to connect to tMDB, trying again in 20 seconds.")
                time.sleep(20)

    def checkLanguage(self, language):
        if not language:
            return None

        if len(language) < 2:
            self.log.error("Unable to set tag language [tag-language].")
            return None

        try:
            from babelfish import Language
        except:
            self.log.exception("Unable to important Language from babelfish [tag-language].")
            return None
        if len(language) == 2:
            try:
                return Language.fromalpha2(language).alpha3
                self.log.exception("Unable to set tag language [tag-language].")
            except:
                return None
        try:
            return Language(language).alpha3
        except:
            self.log.exception("Unable to set tag language [tag-language].")
            return None

    def writeTags(self, mp4Path, artwork=True, thumbnail=False):
        self.log.info("Tagging file: %s." % mp4Path)
        ext = os.path.splitext(mp4Path)[1][1:]
        if ext not in valid_tagging_extensions:
            self.log.error("File is not the correct format.")
            return False

        video = MP4(mp4Path)
        checktags = {}
        checktags["\xa9nam"] = self.title  # Movie title
        checktags["desc"] = self.shortdescription  # Short description
        checktags["ldes"] = self.description  # Long description
        checktags["\xa9day"] = self.date  # Year
        #checktags["stik"] = [9]  # Movie iTunes category
         
        #if self.HD is not None:
        #    checktags["hdvd"] = self.HD
        if self.genre is not None:
            genre = None
            for g in self.genre:
                if genre is None:
                    genre = g['name']
                    break
                # else:
                    # genre += ", " + g['name']
            checktags["\xa9gen"] = genre  # Genre(s)
        #checktags["----:com.apple.iTunes:iTunMOVI"] = self.xml.encode("UTF-8", errors="ignore")  # XML - see xmlTags method
        '''
        rating = self.rating()
        if rating is not None:
            checktags["----:com.apple.iTunes:iTunEXTC"] = rating
        '''

        if artwork:
            path = self.getArtwork(mp4Path)
            if path is not None:
                cover = open(path, 'rb').read()
                if path.endswith('png'):
                    checktags["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_PNG)]  # png poster
                else:
                    checktags["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_JPEG)]  # jpeg poster
        
        ProcessTags = False
        for keys, values in checktags.items():
            if video.tags == None:
                ProcessTags = True
                break
            elif keys in video.tags:
                if video.tags[keys] != [values]:
                    self.log.info(keys + " tag does not match and will be updated")
                    ProcessTags = True
                    break
            else:
                self.log.debug(keys + " will be added")
                ProcessTags = True
        if not ProcessTags:
            self.log.info("All MP4 tags match the original, skipping tagging.")
        else:
            try:
                video.delete()
            except IOError:
                self.log.debug("Unable to clear original tags, attempting to proceed.")

            video["\xa9nam"] = self.title  # Movie title
            video["desc"] = self.shortdescription  # Short description
            video["ldes"] = self.description  # Long description
            video["\xa9day"] = self.date  # Year
            #video["stik"] = [9]  # Movie iTunes category
            #if self.HD is not None:
            #    video["hdvd"] = self.HD
            if self.genre is not None:
                genre = None
                for g in self.genre:
                    if genre is None:
                        genre = g['name']
                        break
                    # else:
                        # genre += ", " + g['name']
                video["\xa9gen"] = genre  # Genre(s)
            #video["----:com.apple.iTunes:iTunMOVI"] = self.xml.encode("UTF-8", errors="ignore")  # XML - see xmlTags method

            '''
            rating = self.rating()
            if rating is not None:
                video["----:com.apple.iTunes:iTunEXTC"] = rating
            '''

            if artwork:
                path = self.getArtwork(mp4Path)
                if path is not None:
                    cover = open(path, 'rb').read()
                    if path.endswith('png'):
                        video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_PNG)]  # png poster
                    else:
                        video["covr"] = [MP4Cover(cover, MP4Cover.FORMAT_JPEG)]  # jpeg poster
            if self.original:
                video["\xa9too"] = "MDH:" + os.path.basename(self.original)
            else:
                video["\xa9too"] = "MDH:" + os.path.basename(mp4Path)

            for i in range(3):
                try:
                    self.log.info("Trying to write tags.")
                    video.save()
                    self.log.info("Tags written successfully.")
                    return True
                except IOError as e:
                    self.log.info("Exception: %s" % e)
                    self.log.exception("There was a problem writing the tags. Retrying.")
                    time.sleep(5)
            return False
        
    def rating(self):
        ratings = {'G': '100',
                        'PG': '200',
                        'PG-13': '300',
                        'R': '400',
                        'NC-17': '500'}
        output = None
        mpaa = self.rating
        if mpaa in ratings:
            numerical = ratings[mpaa]
            output = 'mpaa|' + mpaa.capitalize() + '|' + numerical + '|'
        return str(output)

    def setHD(self, width, height):
        if width >= 1900 or height >= 1060:
            self.HD = [2]
        elif width >= 1260 or height >= 700:
            self.HD = [1]
        else:
            self.HD = [0]

    def xmlTags(self):
        # constants
        header = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\"><plist version=\"1.0\"><dict>\n"
        castheader = "<key>cast</key><array>\n"
        writerheader = "<key>screenwriters</key><array>\n"
        directorheader = "<key>directors</key><array>\n"
        producerheader = "<key>producers</key><array>\n"
        subfooter = "</array>\n"
        footer = "</dict></plist>\n"

        output = StringIO()
        output.write(header)

        # Write actors
        output.write(castheader)
        for a in self.credit['cast'][:5]:
            if a is not None:
                output.write("<dict><key>name</key><string>%s</string></dict>\n" % a['name'])
        output.write(subfooter)
        # Write screenwriters
        output.write(writerheader)
        for w in [x for x in self.credit['crew'] if x['department'].lower() == "writing"][:5]:
            if w is not None:
                output.write("<dict><key>name</key><string>%s</string></dict>\n" % w['name'])
        output.write(subfooter)
        # Write directors
        output.write(directorheader)
        for d in [x for x in self.credit['crew'] if x['department'].lower() == "directing"][:5]:
            if d is not None:
                output.write("<dict><key>name</key><string>%s</string></dict>\n" % d['name'])
        output.write(subfooter)
        # Write producers
        output.write(producerheader)
        for p in [x for x in self.credit['crew'] if x['department'].lower() == "production"][:5]:
            if p is not None:
                output.write("<dict><key>name</key><string>%s</string></dict>\n" % p['name'])
        output.write(subfooter)

        # Write final footer
        output.write(footer)
        return output.getvalue()

    def getArtwork(self, mp4Path, filename='cover'):
        # Check for local artwork in the same directory as the mp4
        extensions = valid_poster_extensions
        poster = None
        for e in extensions:
            head, tail = os.path.split(os.path.abspath(mp4Path))
            path = os.path.join(head, filename + os.extsep + e)
            if (os.path.exists(path)):
                poster = path
                self.log.info("Local artwork detected, using %s." % path)
                break
        # Pulls down all the poster metadata for the correct season and sorts them into the Poster object
        if poster is None:
            poster_path = self.movie['poster_path']
            if not poster_path:
                self.log.warning("No poster found")
                return None
            savepath = os.path.join(tempfile.gettempdir(), "poster-%s.jpg" % self.imdbid)
            if os.path.exists(savepath):
                try:
                    os.remove(savepath)
                except:
                    import random
                    savepath = os.path.join(tempfile.gettempdir(), "poster-%s%s.jpg" % (self.imdbid, random.randint(1, 9999)))
            try:
                poster = urlretrieve("https://image.tmdb.org/t/p/original" + poster_path, savepath)[0]
            except Exception as e:
                self.log.exception("Exception while retrieving poster %s.", str(e))
                poster = None
        return poster


def main():
    if len(sys.argv) > 2:
        mp4 = str(sys.argv[1]).replace("\\", "\\\\").replace("\\\\\\\\", "\\\\")
        imdb_id = str(sys.argv[2])
        tmdb_mp4_instance = tmdb_mp4(imdb_id)
        if os.path.splitext(mp4)[1][1:] in valid_output_extensions:
            tmdb_mp4_instance.writeTags(mp4)
        else:
            print("Wrong file type")


if __name__ == '__main__':
    main()
