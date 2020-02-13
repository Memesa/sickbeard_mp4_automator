#!/usr/bin/env python

import sys
import os
import guessit
import locale
import glob
import argparse
import struct
import logging
import re
import xml
from extensions import valid_tagging_extensions
from readSettings import ReadSettings
from tvdb_mp4 import Tvdb_mp4
from tmdb_mp4 import tmdb_mp4
from mkvtomp4 import MkvtoMp4
from post_processor import PostProcessor
import tmdbsimple as tmdb 
from extensions import tmdb_api_key
from logging.config import fileConfig
import traceback

if sys.version[0] == "3":
    raw_input = input

logpath = '/var/log/sickbeard_mp4_automator'
if os.name == 'nt':
    logpath = os.path.dirname(sys.argv[0])
elif not os.path.isdir(logpath):
    try:
        os.mkdir(logpath)
    except:
        logpath = os.path.dirname(sys.argv[0])
configPath = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), 'logging.ini')).replace("\\", "\\\\")
logPath = os.path.abspath(os.path.join(logpath, 'index.log')).replace("\\", "\\\\")
fileConfig(configPath, defaults={'logfilename': logPath})

log = logging.getLogger("MANUAL")
logging.getLogger("subliminal").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("enzyme").setLevel(logging.WARNING)
logging.getLogger("qtfaststart").setLevel(logging.CRITICAL)

log.info("Manual processor started.")

settings = ReadSettings(os.path.dirname(sys.argv[0]), "autoProcess.ini", logger=log)


def mediatype():
    print("Select media type:")
    print("1. Movie (via IMDB ID)")
    print("2. Movie (via TMDB ID)")
    print("3. TV")
    print("4. Convert without tagging")
    print("5. Skip file")
    result = raw_input("#: ")
    try:
        if 0 < int(result) < 6:
            return int(result)
        else:
            safePrint("Invalid selection")
            return mediatype()
    except:
        safePrint("Invalid selection")
        return mediatype()


def getValue(prompt, num=False):
    print(prompt + ":")
    value = raw_input("#: ").strip(' \"')
    # Remove escape characters in non-windows environments
    if os.name != 'nt':
        value = value.replace('\\', '')
    try:
        value = value.decode(sys.stdout.encoding)
    except:
        pass
    if num is True and value.isdigit() is False:
        print("Must be a numerical value")
        return getValue(prompt, num)
    else:
        return value


def getYesNo():
    yes = ['y', 'yes', 'true', '1']
    no = ['n', 'no', 'false', '0']
    data = raw_input("# [y/n]: ")
    if data.lower() in yes:
        return True
    elif data.lower() in no:
        return False
    else:
        print("Invalid selection")
        return getYesNo()


def getinfo(fileName=None, silent=False, tag=True, tvdbid=None):
    tagdata = None
    def getDataFromNFO(fileName):
        #print(fileName)
        tagNfoFile = None
        path = os.path.abspath(fileName)
        input_dir, filename = os.path.split(path)
        filename, input_extension = os.path.splitext(filename)
        if "Plex Versions" in input_dir:
            checkForNFO_dir = os.path.join(input_dir[:input_dir.index("Plex Versions")], analyseHomeTitle(filename)[1])
        else:
            checkForNFO_dir = input_dir
        try:
            checkForNFO_dir = checkForNFO_dir.decode(sys.getfilesystemencoding())
        except AttributeError:
            pass
        #print(checkForNFO_dir)
        for fileInSourceDir in os.listdir(checkForNFO_dir):
            if fileInSourceDir.lower() == filename.lower() + ".nfo":
                tagNfoFile = os.path.join(checkForNFO_dir, fileInSourceDir)
        if tagNfoFile:
            try:
                with open(tagNfoFile) as openedFile:
                    tagNFOfileRead = openedFile.read().decode("cp1252").replace("&", "&amp;")
                #print(repr(tagNFOfileRead))_
                tree = xml.etree.ElementTree.fromstring(tagNFOfileRead.encode("utf-8"))
                #xmlparser = xml.etree.ElementTree.XMLParser(encoding="cp1252")
                #xmlparser = xml.etree.ElementTree.XMLParser(encoding="utf-8")
                #tree = xml.etree.ElementTree.parse(tagNfoFile, parser=xmlparser)
            except xml.etree.ElementTree.ParseError:
                print("Found nfo file but this is in an invalid XML format and is therefore skipped.")
                return
            return [4,tagNfoFile, tree] 
    NFOdata = getDataFromNFO(fileName)
    if NFOdata:
        return NFOdata
    
    # Try to guess the file is guessing is enabled
    if fileName is not None:
        try:
            tagdata = guessInfo(fileName.decode(sys.getfilesystemencoding()), tvdbid)
        except AttributeError:
            tagdata = guessInfo(fileName, tvdbid)

    if silent is False or not tagdata:
        if tagdata:
            print("Proceed using guessed identification from filename?")
            if getYesNo():
                return tagdata
        else:
            print("Unable to determine identity based on filename, must enter manually")
        m_type = mediatype()
        if m_type == 3:
            tvdbid = getValue("Enter TVDB Series ID", True)
            season = getValue("Enter Season Number", True)
            episode = getValue("Enter Episode Number", True)
            return m_type, tvdbid, season, episode
        elif m_type == 1:
            imdbid = getValue("Enter IMDB ID")
            return m_type, imdbid
        elif m_type == 2:
            tmdbid = getValue("Enter TMDB ID", True)
            return m_type, tmdbid
        elif m_type == 4:
            return None
        elif m_type == 5:
            return False
    else:
        if tagdata and tag:
            return tagdata
        else:
            return None


def guessInfo(fileName, tvdbid=None):
    if tvdbid:
###### old
#        guess = guessit.guess_episode_info(fileName)
#        return tvInfo(guess, tvdbid)
#    if not settings.fullpathguess:
#        fileName = os.path.basename(fileName_orig)
#    else:
#        drive = os.path.splitdrive(fileName_orig)[0]
#        if drive[drive.rfind('\\'):] == ":":
#           drive = ""
#        else:
#            drive = drive[drive.rfind('\\')+1:]
#            #drive = os.path.splitdrive(fileName)[0]
#        fileName = drive + os.path.splitdrive(fileName_orig)[1]
#    fileName = fileName_orig
#    print(fileName)
#    guess = guessit.guessit(fileName)
#    guess['source'] = fileName
#    print(guess)
#######
        guess = guessit.guessit(fileName)
        return tvInfo(guess, tvdbid)
    if not settings.fullpathguess:
        fileName = os.path.basename(fileName)
    guess = guessit.guessit(fileName)
#######
    try:
        if guess['type'] == 'movie':
            return movieInfo(guess)
        elif guess['type'] == 'episode':
            return tvInfo(guess, tvdbid)
        else:
            return None
    except Exception as e:
        print(e)
        return None


def movieInfo(guessData):
    tmdb.API_KEY = tmdb_api_key
    search = tmdb.Search()
    title = guessData['title']
    if 'year' in guessData:
        response = search.movie(query=title, year=guessData["year"])
        if len(search.results) < 1:
            response = search.movie(query=title, year=guessData["year"])
    else:
        response = search.movie(query=title)
    if len(search.results) < 1:
        return None
    result = search.results[0]
    release = result['release_date']
    tmdbid = result['id']
    safePrint("Matched movie title as: %s %s (TMDB ID: %d)" % (title, release, int(tmdbid)))
    return 2, tmdbid
    return None


def tvInfo(guessData, tvdbid=None):
    tmdb.API_KEY = tmdb_api_key
    season = guessData["season"]
    episode = guessData["episode"]
    if not tvdbid:
        search = tmdb.Search()
        series = guessData["title"]
        if 'year' in guessData:
            response = search.tv(query=series, first_air_date_year=guessData["year"])
            if len(search.results) < 1:
                response = search.tv(query=series)
        else:
            response = search.tv(query=series)
        if len(search.results) < 1:
            return None
        result = search.results[0]
        tvdbid = result['id']
    else:
        seriesquery = tmdb.TV(tvdbid)
        showdata = seriesquery.info()
        series = showdata['name']
    safePrint("Matched TV episode as %s (TMDB ID:%d) S%02dE%02d" % (series, int(tvdbid), int(season), int(episode)))
    return 3, tvdbid, season, episode

def analyseHomeTitle(filename):
    try:
        analyseTitle = re.compile('(.*) (\d{4})x(\d*)')
        titleAnalysed = analyseTitle.search(filename)
        reTitle = titleAnalysed.group(1)
        reDate = titleAnalysed.group(2)
        reEpisode = str(int(titleAnalysed.group(3)))
    except AttributeError:
        analyseTitle = re.compile('(.*).(.*)')
        titleAnalysed = analyseTitle.search(filename)
        reTitle = titleAnalysed.group(1)
        reDate = '0'
        reEpisode = '0'
    return (reTitle, reDate, reEpisode)
    
class home_mp4(Tvdb_mp4):
    def __init__(self, tagNfoFile, root, logger=None):
        import logging
        if logger:
            self.log = logger
        else:
            self.log = logging.getLogger(__name__)
        
        self.show = None
        self.title = None
        self.genre = None
        self.description = None
        self.network = None
        self.airdate = None
        self.season = None
        self.episode = None
        self.seasondata = None

        # while True:
            # try:
                # #with open(tagNfoFile) as tNFOf:
                # #    tagNFOfileData = tNFOf.read().decode("cp437")
                # xmlparser = xml.etree.ElementTree.XMLParser(encoding="cp1252")
                # tree = xml.etree.ElementTree.parse(tagNfoFile, parser=xmlparser)
                # break
            # except xml.etree.ElementTree.ParseError:
                # raw_input("Error - something is wrong with the .nfo file (likely a difficult character), plese fix it then press Enter to try again.")
        #root = tree.getroot()
        
        self.show = "- Thuis Videos -"
        if root.find("title") is not None:
            self.title = root.find("title").text
        if root.find("genre") is not None:
            self.genre = " " + root.find("genre").text + " "
        else:
            self.genre = " Home Video "
        if root.find("plot") is not None:
            self.description = root.find("plot").text
        if root.find("set") is not None:
            self.season = root.find("set").text
            self.airdate = root.find("set").text + "-01-01"
        else:
            self.airdate = reInfo[1] + "-01-01"
            self.season = reInfo[1]
        
        path = os.path.abspath(tagNfoFile)
        input_dir, filename = os.path.split(path)
        
        reInfo = analyseHomeTitle(filename)
        # analyseTitle = re.compile('(.*) (\d{4})x(\d*)')
        # titleAnalysed = analyseTitle.search(filename)
        if not self.title:
            self.title = reInfo[0]
        self.episode = reInfo[2]
        if not self.seasondata:
            self.seasondata = []
        # print(self.show)
        # print(self.title)
        print(repr(self.title))
        print(self.title.encode("CP1252"))
        # print(self.genre)
        # print(self.description)
        # print(self.airdate)
        # print(self.season)
        # print(self.episode)
        # print(self.seasondata)
        

def processFile(inputfile, tagdata, converter, info=None, relativePath=None):
    # Process
    info = info if info else converter.isValidSource(inputfile)
    if not info:
        return

    # Gather tagdata
    if tagdata is False:
        return  # This means the user has elected to skip the file
    elif tagdata is None:
        tagmp4 = None  # No tag data specified but convert the file anyway
    elif tagdata[0] == 1:
        imdbid = tagdata[1]
        tagmp4 = tmdb_mp4(imdbid, language=settings.taglanguage, logger=log)
        safePrint("Processing %s" % (tagmp4.title))
    elif tagdata[0] == 2:
        tmdbid = tagdata[1]
        tagmp4 = tmdb_mp4(tmdbid, True, language=settings.taglanguage, logger=log)
        safePrint("Processing %s" % (tagmp4.title))
    elif tagdata[0] == 3:
        tvdbid = int(tagdata[1])
        season = int(tagdata[2])
        episode = int(tagdata[3])
        tagmp4 = Tvdb_mp4(tvdbid, season, episode, language=settings.taglanguage, logger=log, tmdbid=True)
        safePrint("Processing %s Season %02d Episode %02d - %s" % (tagmp4.show, int(tagmp4.season), int(tagmp4.episode), tagmp4.title))
    elif tagdata[0] == 4:
        tagNfoFile = tagdata[1]
        tree = tagdata[2]
        tagmp4 = home_mp4(tagNfoFile, tree, logger=log)
        safePrint("Processing %s" % (tagmp4.title))

    output = converter.process(inputfile, True)
    if output:
        if tagmp4 is not None and output['output_extension'] in valid_tagging_extensions:
            try:
                tagmp4.setHD(output['x'], output['y'])
                tagmp4.writeTags(output['output'], settings.artwork, settings.thumbnail)
            except Exception as e:
                log.exception("There was an error tagging the file")
                print("There was an error tagging the file")
                print(e)
        if settings.relocate_moov and output['output_extension'] in valid_tagging_extensions:
            converter.QTFS(output['output'])
        output_files = converter.replicate(output['output'], relativePath=relativePath)
        if settings.postprocess:
            post_processor = PostProcessor(output_files)
            if tagdata:
                if tagdata[0] == 1:
                    post_processor.setMovie(tagdata[1])
                elif tagdata[0] == 2:
                    post_processor.setMovie(tagdata[1])
                elif tagdata[0] == 3:
                    post_processor.setTV(tagdata[1], tagdata[2], tagdata[3])
            post_processor.run_scripts()
    else:
        log.error("File is not in the correct format")


def walkDir(dir, silent=False, preserveRelative=False, tvdbid=None, tag=True, optionsOnly=False):
    files = []
    converter = MkvtoMp4(settings, logger=log)
    for r, d, f in os.walk(dir):
        for file in f:
            files.append(os.path.join(r, file))
    for filepath in files:
        info = converter.isValidSource(filepath)
        if info:
            safePrint("Processing file %s" % (filepath))
            relative = os.path.split(os.path.relpath(filepath, dir))[0] if preserveRelative else None
            if optionsOnly:
                displayOptions(filepath)
                continue
            if tag:
                tagdata = getinfo(filepath, silent, tvdbid=tvdbid)
            else:
                tagdata = None
            processFile(filepath, tagdata, converter, info=info, relativePath=relative)


def displayOptions(path):
    converter = MkvtoMp4(settings)
    safePrint(converter.jsonDump(path))


def safePrint(text):
    try:
        print(text)
    except:
        try:
            print(text.encode('utf-8', errors='ignore'))
        except:
            pass


def main():
    global settings

    parser = argparse.ArgumentParser(description="Manual conversion and tagging script for sickbeard_mp4_automator")
    parser.add_argument('-i', '--input', help='The source that will be converted. May be a file or a directory')
    parser.add_argument('-c', '--config', help='Specify an alternate configuration file location')
    parser.add_argument('-a', '--auto', action="store_true", help="Enable auto mode, the script will not prompt you for any further input, good for batch files. It will guess the metadata using guessit")
    parser.add_argument('-tv', '--tvid', help="Set the TMDB ID for a tv show")
    parser.add_argument('-s', '--season', help="Specifiy the season number")
    parser.add_argument('-e', '--episode', help="Specify the episode number")
    parser.add_argument('-imdb', '--imdbid', help="Specify the IMDB ID for a movie")
    parser.add_argument('-tmdb', '--tmdbid', help="Specify TMDB ID for a movie")
    parser.add_argument('-nm', '--nomove', action='store_true', help="Overrides and disables the custom moving of file options that come from output_dir and move-to")
    parser.add_argument('-nc', '--nocopy', action='store_true', help="Overrides and disables the custom copying of file options that come from output_dir and move-to")
    parser.add_argument('-nd', '--nodelete', action='store_true', help="Overrides and disables deleting of original files")
    parser.add_argument('-nt', '--notag', action="store_true", help="Overrides and disables tagging when using the automated option")
    parser.add_argument('-np', '--nopost', action="store_true", help="Overrides and disables the execution of additional post processing scripts")
    parser.add_argument('-pr', '--preserveRelative', action='store_true', help="Preserves relative directories when processing multiple files using the copy-to or move-to functionality")
    parser.add_argument('-cmp4', '--convertmp4', action='store_true', help="Overrides convert-mp4 setting in autoProcess.ini enabling the reprocessing of mp4 files")
    parser.add_argument('-fc', '--forceconvert', action='store_true', help="Overrides force-convert setting in autoProcess.ini and also enables convert-mp4 if true forcing the conversion of mp4 files")
    parser.add_argument('-m', '--moveto', help="Override move-to value setting in autoProcess.ini changing the final destination of the file")
    parser.add_argument('-oo', '--optionsonly', action="store_true", help="Display generated conversion options only, do not perform conversion")

    args = vars(parser.parse_args())

    # Setup the silent mode
    silent = args['auto']
    tag = True

    safePrint("%sbit Python." % (struct.calcsize("P") * 8))

    # Settings overrides
    if(args['config']):
        if os.path.exists(args['config']):
            safePrint('Using configuration file "%s"' % (args['config']))
            settings = ReadSettings(os.path.split(args['config'])[0], os.path.split(args['config'])[1], logger=log)
        elif os.path.exists(os.path.join(os.path.dirname(sys.argv[0]), args['config'])):
            safePrint('Using configuration file "%s"' % (args['config']))
            settings = ReadSettings(os.path.dirname(sys.argv[0]), args['config'], logger=log)
        else:
            safePrint('Configuration file "%s" not present, using default autoProcess.ini' % (args['config']))
    if (args['nomove']):
        settings.output_dir = None
        settings.moveto = None
        print("No-move enabled")
    elif (args['moveto']):
        settings.moveto = args['moveto']
        safePrint("Overriden move-to to " + args['moveto'])
    if (args['nocopy']):
        settings.copyto = None
        print("No-copy enabled")
    if (args['nodelete']):
        settings.delete = False
        print("No-delete enabled")
    if (args['convertmp4']):
        settings.processMP4 = True
        print("Reprocessing of MP4 files enabled")
    if (args['forceconvert']):
        settings.forceConvert = True
        settings.processMP4 = True
        print("Force conversion of mp4 files enabled. As a result conversion of mp4 files is also enabled")
    if (args['notag']):
        settings.tagfile = False
        print("No-tagging enabled")
    if (args['nopost']):
        settings.postprocess = False
        print("No post processing enabled")
    if (args['optionsonly']):
        logging.getLogger("mkvtomp4").setLevel(logging.CRITICAL)
        print("Options only mode enabled")

    # Establish the path we will be working with
    if (args['input']):
        path = (str(args['input']))
        try:
            path = glob.glob(path)[0]
        except:
            pass
    else:
        path = getValue("Enter path to file")

    tvdbid = int(args['tvid']) if args['tvid'] else None

    if os.path.isdir(path):
        walkDir(path, silent, tvdbid=tvdbid, preserveRelative=args['preserveRelative'], tag=settings.tagfile, optionsOnly=args['optionsonly'])
    elif (os.path.isfile(path)):
        converter = MkvtoMp4(settings, logger=log)
        info = converter.isValidSource(path)
        if info:
            if (args['optionsonly']):
                displayOptions(path)
                return
            if (not settings.tagfile):
                tagdata = None
            elif (args['tvid'] and not (args['imdbid'] or args['tmdbid'])):
                season = int(args['season']) if args['season'] else None
                episode = int(args['episode']) if args['episode'] else None
                if (tvdbid and season and episode):
                    tagdata = [3, tvdbid, season, episode]
                else:
                    tagdata = getinfo(path, silent=silent, tvdbid=tvdbid)
            elif ((args['imdbid'] or args['tmdbid']) and not args['tvdbid']):
                if (args['imdbid']):
                    imdbid = args['imdbid']
                    tagdata = [1, imdbid]
                elif (args['tmdbid']):
                    tmdbid = int(args['tmdbid'])
                    tagdata = [2, tmdbid]
            else:
                tagdata = getinfo(path, silent=silent, tvdbid=tvdbid)
            processFile(path, tagdata, converter, info=info)
        else:
            safePrint("File %s is not in a valid format" % (path))
            tagdata = getinfo(path, silent=silent, tvdbid=tvdbid)
            if tagdata is None:
                raw_input('no data found :(')
            processFile(path, tagdata)
    else:
        safePrint("File %s does not exist" % (path))


if __name__ == '__main__':
    main()
